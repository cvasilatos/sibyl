import json
import logging
import os
import shutil
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from chromadb.api import ClientAPI
    from chromadb.api.models.Collection import Collection
    from decima.logger import CustomLogger


import chromadb
from chromadb.config import Settings

from sibyl.config import MAX_SCORE, STORAGE_PATH
from sibyl.services.reviewer import PaperReview
from sibyl.storage.review import Review

# Maximum number of characters to include in a review summary preview
_REVIEW_SUMMARY_MAX_LEN: int = 200

_SECTION_LABELS = {
    "novelty": "Novelty",
    "methodology": "Methodology",
    "results": "Results",
    "clarity": "Clarity",
    "impact": "Impact",
    "strengths": "Strengths",
    "limitations": "Limitations",
    "detailed_feedback": "Detailed Feedback",
}


def _summary_source(criteria: dict) -> str:
    """Return the text the library summary is cut from: the default review's feedback, or the completed form for form reviews."""
    return str(criteria.get("detailed_feedback") or criteria.get("review_form_response") or "")


_EMBEDDING_MODEL = "nomic-embed-text"

Embedder = Callable[[str], list[float]]


def embedding_backend() -> str:
    """Return ``ollama`` or ``local`` (Chroma's bundled MiniLM, no server needed).

    Defaults to Ollama embeddings when the Ollama engine is used, and local embeddings otherwise.
    """
    configured = os.getenv("SIBYL_EMBEDDINGS", "").strip().lower()
    if configured in {"ollama", "local"}:
        return configured
    return "ollama" if os.getenv("SIBYL_ENGINE", "ollama").strip().lower() == "ollama" else "local"


def _ollama_embedder() -> Embedder:
    from ollama import Client, ResponseError  # noqa: PLC0415

    from sibyl.inference.ollama_engine import ollama_hosts_from_env  # noqa: PLC0415

    client = Client(host=ollama_hosts_from_env()[0])

    def embed(text: str) -> list[float]:
        try:
            return list(client.embeddings(model=_EMBEDDING_MODEL, prompt=text[:5000], keep_alive=0).embedding)
        except ResponseError as e:
            if e.status_code != 404:  # noqa: PLR2004
                raise
            logging.getLogger(__name__).info(f"Embedding model {_EMBEDDING_MODEL} missing; pulling it once")
            client.pull(_EMBEDDING_MODEL)
            return list(client.embeddings(model=_EMBEDDING_MODEL, prompt=text[:5000], keep_alive=0).embedding)

    return embed


def _local_embedder() -> Embedder:
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction  # noqa: PLC0415

    function = DefaultEmbeddingFunction()

    def embed(text: str) -> list[float]:
        return [float(x) for x in function([text[:5000]])[0]]

    return embed


class Engine:
    """Vector database storage for reviews with semantic search using ChromaDB."""

    def __init__(self, storage_path: str | Path = STORAGE_PATH, embeddings: str | None = None) -> None:
        """Initialize the storage system.

        Args:
            storage_path: Path to the storage directory for ChromaDB and PDFs; defaults to ``SIBYL_STORAGE_PATH``
            embeddings: ``ollama`` or ``local``; defaults to :func:`embedding_backend`

        """
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.pdf_storage: Path = self.storage_path / "pdfs"
        self.pdf_storage.mkdir(exist_ok=True)

        self.embeddings = embeddings or embedding_backend()
        self.logger.debug(f"Initializing at {storage_path}, embeddings={self.embeddings}")

        self.client: ClientAPI = chromadb.PersistentClient(
            path=str(self.storage_path / "chromadb"),
            settings=Settings(anonymized_telemetry=False),
        )

        self._embedder: Embedder | None = None

        # Embedding dimensions differ between backends, so each backend has its own collection.
        self.collection: Collection = self.client.get_or_create_collection(
            name="paper_reviews" if self.embeddings == "ollama" else "paper_reviews_local",
            metadata={"hnsw:space": "cosine"},
        )
        self.logger.info(f"Initialized with {self.collection.count()} existing reviews")

    def _generate_embedding(self, text: str) -> list[float]:
        self.logger.debug(f"Generating {self.embeddings} embedding for text ({len(text)} chars)")
        if self._embedder is None:
            self._embedder = _ollama_embedder() if self.embeddings == "ollama" else _local_embedder()
        return self._embedder(text)

    def save_review(self, review: PaperReview, pdf_filename: str, pdf_path: str | Path | None = None, paper_text: str | None = None) -> str:
        """Save a review to the vector database.

        Args:
            review: The PaperReview object to save
            pdf_filename: Original filename of the PDF
            pdf_path: Optional path to the PDF file to store
            paper_text: Optional full text of the paper

        Returns:
            ID of the saved review

        """
        review_id = f"review_{uuid.uuid4().hex}"

        self.logger.info(f"Saving review for paper '{review.paper_title}' (model={review.reviewer_model}, score={review.criteria.score})")

        stored_pdf_path = None
        if pdf_path and Path(pdf_path).exists():
            stored_pdf_path = self.pdf_storage / f"{review_id}.pdf"
            shutil.copy2(pdf_path, stored_pdf_path)
            stored_pdf_path = str(stored_pdf_path)

        criteria = review.criteria
        sections = [(label, getattr(criteria, field)) for field, label in _SECTION_LABELS.items()]
        searchable_content = "\n".join(
            [
                f"Title: {review.paper_title}",
                f"Reviewer: {review.reviewer_model}",
                f"Score: {criteria.score}/{MAX_SCORE}",
                f"Recommendation: {criteria.recommendation}",
                *(f"{label}: {text}" for label, text in sections if text),
            ]
        )
        if criteria.review_form_response:
            searchable_content += f"\n\nCompleted Review Form:\n{criteria.review_form_response}"

        if paper_text:
            searchable_content += f"\n\nPaper Content: {paper_text}"

        embedding = self._generate_embedding(searchable_content)

        metadata = {
            "paper_title": review.paper_title,
            "pdf_filename": pdf_filename,
            "pdf_path": stored_pdf_path or "",
            "reviewer_model": review.reviewer_model,
            "score": review.criteria.score,
            "recommendation": review.criteria.recommendation,
            "created_at": datetime.now(tz=UTC).isoformat(),
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

        reviews: list[Review] = []
        result_ids = results["ids"]
        result_metadatas = results["metadatas"]
        result_distances = results["distances"]
        if result_ids and result_ids[0] and result_metadatas is not None:
            for i, review_id in enumerate(result_ids[0]):
                metadata = cast("dict[str, str | int | float | bool | None]", result_metadatas[0][i])
                distance = float(result_distances[0][i]) if result_distances is not None else 0.0
                similarity = 1 - distance

                review_data = json.loads(str(metadata.get("review_json", "{}")))

                feedback = _summary_source(review_data.get("criteria", {}))
                review_summary = feedback[:_REVIEW_SUMMARY_MAX_LEN] + ("..." if len(feedback) > _REVIEW_SUMMARY_MAX_LEN else "")

                reviews.append(
                    Review(
                        id=review_id,
                        paper_title=str(metadata.get("paper_title", "")),
                        pdf_filename=str(metadata.get("pdf_filename", "")),
                        pdf_path=str(metadata["pdf_path"]) if metadata.get("pdf_path") else None,
                        reviewer_model=str(metadata.get("reviewer_model", "")),
                        score=cast("int", metadata.get("score", 0)),
                        recommendation=str(metadata.get("recommendation", "")),
                        review_summary=review_summary,
                        created_at=str(metadata.get("created_at", "")),
                        similarity_score=similarity,
                    )
                )

        self.logger.debug(f"Search returned {len(reviews)} results")
        return reviews

    def list_reviews(self, limit: int = 50, offset: int = 0, search: str | None = None) -> list[Review]:
        """List all reviews with pagination and optional text filtering.

        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip
            search: Optional text query to filter reviews by title, model, or recommendation

        Returns:
            List of Review objects

        """
        all_results = self.collection.get(
            limit=limit if not search else None,
            offset=offset if not search else None,
            include=["metadatas"],
        )

        search_lower = search.lower() if search else None

        reviews: list[Review] = []
        result_ids = all_results["ids"]
        result_metadatas = all_results["metadatas"]
        if result_ids and result_metadatas is not None:
            for i, review_id in enumerate(result_ids):
                metadata = cast("dict[str, str | int | float | bool | None]", result_metadatas[i])

                if search_lower and not any(
                    search_lower in str(metadata.get(field) or "").lower() for field in ("paper_title", "pdf_filename", "reviewer_model", "recommendation")
                ):
                    continue

                review_data = json.loads(str(metadata.get("review_json", "{}")))

                feedback = _summary_source(review_data.get("criteria", {}))
                review_summary = feedback[:_REVIEW_SUMMARY_MAX_LEN] + ("..." if len(feedback) > _REVIEW_SUMMARY_MAX_LEN else "")

                reviews.append(
                    Review(
                        id=review_id,
                        paper_title=str(metadata.get("paper_title", "")),
                        pdf_filename=str(metadata.get("pdf_filename", "")),
                        pdf_path=str(metadata["pdf_path"]) if metadata.get("pdf_path") else None,
                        reviewer_model=str(metadata.get("reviewer_model", "")),
                        score=cast("int", metadata.get("score", 0)),
                        recommendation=str(metadata.get("recommendation", "")),
                        review_summary=review_summary,
                        created_at=str(metadata.get("created_at", "")),
                    )
                )

        return reviews[offset : offset + limit] if search else reviews

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

            result_metadatas = results["metadatas"]
            if result_metadatas is None:
                return None

            metadata = cast("dict[str, str | int | float | bool | None]", result_metadatas[0])
            review_data = json.loads(str(metadata.get("review_json", "{}")))

            return {
                "id": review_id,
                "paper_title": str(metadata.get("paper_title", "")),
                "pdf_filename": str(metadata.get("pdf_filename", "")),
                "pdf_path": str(metadata["pdf_path"]) if metadata.get("pdf_path") else None,
                "reviewer_model": str(metadata.get("reviewer_model", "")),
                "score": cast("int", metadata.get("score", 0)),
                "recommendation": str(metadata.get("recommendation", "")),
                "created_at": str(metadata.get("created_at", "")),
                "criteria": review_data.get("criteria", {}),
                "raw_response": review_data.get("raw_response", ""),
            }
        except Exception:
            return None

    def delete_review(self, review_id: str) -> bool:
        """Delete a review by ID.

        Args:
            review_id: ID of the review to delete

        """
        results = self.collection.get(ids=[review_id], include=["metadatas"])

        result_metadatas = results["metadatas"]
        if not results["ids"] or not result_metadatas:
            return False

        metadata = cast("dict[str, str | int | float | bool | None]", result_metadatas[0])
        pdf_path = str(metadata["pdf_path"]) if metadata.get("pdf_path") else None
        if pdf_path and Path(pdf_path).exists():
            Path(pdf_path).unlink()

        self.collection.delete(ids=[review_id])
        self.logger.info(f"Review deleted: {review_id}")
        return True

    def delete_all_reviews(self) -> int:
        """Delete all reviews from storage.

        Returns:
            Number of reviews deleted

        """
        all_results = self.collection.get(include=["metadatas"])

        if not all_results["ids"]:
            return 0

        result_metadatas = all_results["metadatas"]
        if result_metadatas is not None:
            for metadata in result_metadatas:
                typed_meta = cast("dict[str, str | int | float | bool | None]", metadata)
                pdf_path = str(typed_meta["pdf_path"]) if typed_meta.get("pdf_path") else None
                if pdf_path and Path(pdf_path).exists():
                    Path(pdf_path).unlink()

        self.collection.delete(ids=all_results["ids"])
        count = len(all_results["ids"])
        self.logger.info(f"Deleted all {count} reviews")
        return count

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
                "unique_papers": 0,
                "unique_models": 0,
                "recommendations": {},
            }

        result_metadatas = all_results["metadatas"] or []
        metas = [cast("dict[str, str | int | float | bool | None]", m) for m in result_metadatas]

        papers = {str(m.get("paper_title", "")) for m in metas}
        models = {str(m.get("reviewer_model", "")) for m in metas}

        recommendations: dict[str, int] = {}
        for m in metas:
            rec = str(m.get("recommendation", ""))
            recommendations[rec] = recommendations.get(rec, 0) + 1

        return {
            "total_reviews": len(all_results["ids"]),
            "unique_papers": len(papers),
            "unique_models": len(models),
            "recommendations": recommendations,
        }
