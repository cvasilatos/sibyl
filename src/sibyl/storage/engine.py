import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from chromadb.api.models.Collection import Collection

if TYPE_CHECKING:
    from decimalog.logger import CustomLogger


import chromadb
import requests
from chromadb.config import Settings

from sibyl.config import OLLAMA_BASE_URL
from sibyl.reviewer import PaperReview
from sibyl.storage.review import Review


class Engine:
    """Vector database storage for reviews with semantic search using ChromaDB."""

    def __init__(self, storage_path: str = "./sibyl_storage") -> None:
        """Initialize the storage system.

        Args:
            storage_path: Path to the storage directory for ChromaDB and PDFs
            ollama_url: URL for Ollama API to generate embeddings.
                        Defaults to the OLLAMA_BASE_URL environment variable,
                        falling back to http://localhost:11434.

        """
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.pdf_storage = self.storage_path / "pdfs"
        self.pdf_storage.mkdir(exist_ok=True)

        self.logger.debug(f"Initializing at {storage_path}, ollama_url={OLLAMA_BASE_URL}")

        self.client = chromadb.PersistentClient(
            path=str(self.storage_path / "chromadb"),
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection: Collection = self.client.get_or_create_collection(
            name="paper_reviews",
            metadata={"hnsw:space": "cosine"},
        )
        self.logger.info(f"Initialized with {self.collection.count()} existing reviews")

    def _generate_embedding(self, text: str, model_name: str) -> list[float]:
        """Generate embedding for text using Ollama.

        Args:
            text: Text to generate embedding for
            model_name: Name of the Ollama model to use for embedding generation

        Returns:
            List of embedding values

        """
        self.logger.debug(f"Generating embedding for text ({len(text)} chars), model: {model_name} - {model_name.split(':', maxsplit=1)[0]}")
        try:
            response: requests.Response = requests.post(f"{OLLAMA_BASE_URL}/api/embeddings", json={"model": "nomic-embed-text", "prompt": text[:5000]}, timeout=60)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_details = e.response.json().get("error", e.response.text)
            self.logger.error(f"Failed to generate embedding for text with Ollama: {error_details}")
            return []
        return response.json()["embedding"]

    def save_review(self, review: PaperReview, pdf_filename: str, pdf_path: str | None = None, paper_text: str | None = None) -> str:
        """Save a review to the vector database.

        Args:
            review: The PaperReview object to save
            pdf_filename: Original filename of the PDF
            pdf_path: Optional path to the PDF file to store
            paper_text: Optional full text of the paper

        Returns:
            ID of the saved review

        """
        review_id = f"review_{datetime.now().timestamp()}_{pdf_filename}"

        self.logger.info(f"Saving review for paper '{review.paper_title}' (model={review.reviewer_model}, score={review.criteria.overall_score})")

        stored_pdf_path = None
        if pdf_path and Path(pdf_path).exists():
            stored_pdf_path = self.pdf_storage / f"{review_id}.pdf"
            shutil.copy2(pdf_path, stored_pdf_path)
            stored_pdf_path = str(stored_pdf_path)

        searchable_content = f"""
        Title: {review.paper_title}
        Reviewer: {review.reviewer_model}
        Score: {review.criteria.overall_score}/10
        Recommendation: {review.criteria.recommendation}

        Novelty: {review.criteria.novelty}
        Methodology: {review.criteria.methodology}
        Results: {review.criteria.results}
        Clarity: {review.criteria.clarity}
        Impact: {review.criteria.impact}
        Strengths: {review.criteria.strengths}
        Limitations: {review.criteria.limitations}

        Detailed Feedback: {review.criteria.detailed_feedback}
        """

        searchable_content += f"\n\nPaper Content: {paper_text}"

        embedding = self._generate_embedding(searchable_content, review.reviewer_model)

        metadata = {
            "paper_title": review.paper_title,
            "pdf_filename": pdf_filename,
            "pdf_path": stored_pdf_path or "",
            "reviewer_model": review.reviewer_model,
            "overall_score": review.criteria.overall_score,
            "recommendation": review.criteria.recommendation,
            "created_at": datetime.now().isoformat(),
            "review_json": json.dumps(
                {
                    "paper_title": review.paper_title,
                    "reviewer_model": review.reviewer_model,
                    "criteria": review.criteria.model_dump(),
                    "raw_response": review.raw_response,
                }
            ),
        }

        self.collection.add(
            ids=[review_id],
            embeddings=[embedding],
            documents=[searchable_content],
            metadatas=[metadata],
        )

        self.logger.debug(f"Review saved with id={review_id}")
        return review_id

    def search_reviews(self, query: str, limit: int = 10) -> list[Review]:
        """Search reviews using semantic similarity.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of matching StoredReview objects with similarity scores

        """
        self.logger.info(f"Searching reviews with query='{query}', limit={limit}")
        query_embedding = self._generate_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
        )

        reviews = []
        if results["ids"] and results["ids"][0]:
            for i, review_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if "distances" in results else 0
                similarity = 1 - distance

                review_data = json.loads(metadata["review_json"])

                feedback = review_data["criteria"]["detailed_feedback"]
                review_summary = feedback[:200] + ("..." if len(feedback) > 200 else "")

                reviews.append(
                    Review(
                        id=review_id,
                        paper_title=metadata["paper_title"],
                        pdf_filename=metadata["pdf_filename"],
                        pdf_path=metadata.get("pdf_path"),
                        reviewer_model=metadata["reviewer_model"],
                        overall_score=metadata["overall_score"],
                        recommendation=metadata["recommendation"],
                        review_summary=review_summary,
                        created_at=metadata["created_at"],
                        similarity_score=similarity,
                    )
                )

        self.logger.debug(f"Search returned {len(reviews)} results")
        return reviews

    def list_reviews(self, limit: int = 50, offset: int = 0) -> list[Review]:
        """List all reviews with pagination.

        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of Review objects

        """
        all_results = self.collection.get(
            limit=limit,
            offset=offset,
            include=["metadatas"],
        )

        reviews = []
        if all_results["ids"]:
            for i, review_id in enumerate(all_results["ids"]):
                metadata = all_results["metadatas"][i]
                review_data = json.loads(metadata["review_json"])

                feedback = review_data["criteria"]["detailed_feedback"]
                review_summary = feedback[:200] + ("..." if len(feedback) > 200 else "")

                reviews.append(
                    Review(
                        id=review_id,
                        paper_title=metadata["paper_title"],
                        pdf_filename=metadata["pdf_filename"],
                        pdf_path=metadata.get("pdf_path"),
                        reviewer_model=metadata["reviewer_model"],
                        overall_score=metadata["overall_score"],
                        recommendation=metadata["recommendation"],
                        review_summary=review_summary,
                        created_at=metadata["created_at"],
                    )
                )

        return reviews

    def get_review(self, review_id: str) -> dict | None:
        """Get a specific review by ID with full details.

        Args:
            review_id: ID of the review to retrieve

        Returns:
            Dictionary with full review data or None if not found

        """
        try:
            results = self.collection.get(
                ids=[review_id],
                include=["metadatas", "documents"],
            )

            if not results["ids"]:
                return None

            metadata = results["metadatas"][0]
            review_data = json.loads(metadata["review_json"])

            return {
                "id": review_id,
                "paper_title": metadata["paper_title"],
                "pdf_filename": metadata["pdf_filename"],
                "pdf_path": metadata.get("pdf_path"),
                "reviewer_model": metadata["reviewer_model"],
                "overall_score": metadata["overall_score"],
                "recommendation": metadata["recommendation"],
                "created_at": metadata["created_at"],
                "criteria": review_data["criteria"],
                "raw_response": review_data.get("raw_response", ""),
            }
        except Exception:
            return None

    def delete_review(self, review_id: str) -> None:
        """Delete a review by ID.

        Args:
            review_id: ID of the review to delete

        Returns:
            True if deleted, False if not found

        """
        results = self.collection.get(ids=[review_id], include=["metadatas"])

        metadata = results["metadatas"][0]
        pdf_path = metadata.get("pdf_path")

        if pdf_path and Path(pdf_path).exists():
            Path(pdf_path).unlink()

        self.collection.delete(ids=[review_id])
        self.logger.info(f"Review deleted: {review_id}")

    def count_reviews(self) -> int:
        """Get the total number of reviews in storage.

        Returns:
            Total count of reviews

        """
        return self.collection.count()

    def get_statistics(self) -> dict:
        """Get statistics about stored reviews.

        Returns:
            Dictionary with statistics

        """
        all_results = self.collection.get(include=["metadatas"])

        if not all_results["ids"]:
            return {
                "total_reviews": 0,
                "avg_score": 0,
                "min_score": 0,
                "max_score": 0,
                "unique_papers": 0,
                "unique_models": 0,
                "recommendations": {},
            }

        scores = [m["overall_score"] for m in all_results["metadatas"]]
        papers = set(m["paper_title"] for m in all_results["metadatas"])
        models = set(m["reviewer_model"] for m in all_results["metadatas"])

        recommendations = {}
        for m in all_results["metadatas"]:
            rec = m["recommendation"]
            recommendations[rec] = recommendations.get(rec, 0) + 1

        return {
            "total_reviews": len(all_results["ids"]),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "unique_papers": len(papers),
            "unique_models": len(models),
            "recommendations": recommendations,
        }
