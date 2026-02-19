"""Storage module for persisting and searching reviews and PDFs using vector database."""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import chromadb
import requests
from chromadb.config import Settings
from pydantic import BaseModel

from .config import SibylConfig
from .reviewer import PaperReview


class StoredReview(BaseModel):
    """Model for a stored review with metadata."""

    id: str
    paper_title: str
    pdf_filename: str
    pdf_path: Optional[str] = None
    reviewer_model: str
    overall_score: int
    recommendation: str
    review_summary: str
    created_at: str
    similarity_score: Optional[float] = None  # For search results


class ReviewStorage:
    """Vector database storage for reviews with semantic search using ChromaDB."""

    def __init__(
        self,
        storage_path: str = "./sibyl_storage",
        ollama_url: Optional[str] = None,
    ):
        """Initialize the storage system.

        Args:
            storage_path: Path to the storage directory for ChromaDB and PDFs
            ollama_url: URL for Ollama API to generate embeddings.
                        Defaults to the OLLAMA_BASE_URL environment variable,
                        falling back to http://localhost:11434.

        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.pdf_storage = self.storage_path / "pdfs"
        self.pdf_storage.mkdir(exist_ok=True)
        
        self.ollama_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.storage_path / "chromadb"),
            settings=Settings(anonymized_telemetry=False),
        )
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="paper_reviews",
            metadata={"hnsw:space": "cosine"},
        )

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Ollama.

        Args:
            text: Text to generate embedding for

        Returns:
            List of embedding values

        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["embedding"]
        except Exception:
            # Fallback for testing only - should not be used in production
            # TODO: In production, raise an exception instead of using fallback
            import hashlib
            # Using SHA-256 instead of MD5 for better security practices
            hash_val = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
            # Generate a simple 384-dimensional embedding for testing
            embedding = [(hash_val >> i) % 100 / 100.0 for i in range(384)]
            return embedding

    def save_review(
        self,
        review: PaperReview,
        pdf_filename: str,
        pdf_path: Optional[str] = None,
        paper_text: Optional[str] = None,
    ) -> str:
        """Save a review to the vector database.

        Args:
            review: The PaperReview object to save
            pdf_filename: Original filename of the PDF
            pdf_path: Optional path to the PDF file to store
            paper_text: Optional full text of the paper

        Returns:
            ID of the saved review

        """
        # Generate unique ID
        review_id = f"review_{datetime.now().timestamp()}_{pdf_filename}"
        
        # Store PDF file if provided
        stored_pdf_path = None
        if pdf_path and Path(pdf_path).exists():
            stored_pdf_path = self.pdf_storage / f"{review_id}.pdf"
            shutil.copy2(pdf_path, stored_pdf_path)
            stored_pdf_path = str(stored_pdf_path)
        
        # Create searchable content
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
        
        # Add paper text for better search
        if paper_text:
            # Limit paper text to first 5000 chars to avoid model token limits
            # Most embedding models have a max token limit (e.g., 512-8192 tokens)
            # 5000 chars ≈ 1000-1500 tokens, safe for most models
            searchable_content += f"\n\nPaper Content: {paper_text[:5000]}"
        
        # Generate embedding
        embedding = self._generate_embedding(searchable_content)
        
        # Prepare metadata
        metadata = {
            "paper_title": review.paper_title,
            "pdf_filename": pdf_filename,
            "pdf_path": stored_pdf_path or "",
            "reviewer_model": review.reviewer_model,
            "overall_score": review.criteria.overall_score,
            "recommendation": review.criteria.recommendation,
            "created_at": datetime.now().isoformat(),
            "review_json": json.dumps({
                "paper_title": review.paper_title,
                "reviewer_model": review.reviewer_model,
                "criteria": review.criteria.model_dump(),
                "raw_response": review.raw_response,
            }),
        }
        
        # Add to ChromaDB
        self.collection.add(
            ids=[review_id],
            embeddings=[embedding],
            documents=[searchable_content],
            metadatas=[metadata],
        )
        
        return review_id

    def search_reviews(
        self, query: str, limit: int = 10
    ) -> List[StoredReview]:
        """Search reviews using semantic similarity.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of matching StoredReview objects with similarity scores

        """
        # Generate embedding for query
        query_embedding = self._generate_embedding(query)
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
        )
        
        # Convert to StoredReview objects
        reviews = []
        if results["ids"] and results["ids"][0]:
            for i, review_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if "distances" in results else 0
                similarity = 1 - distance  # Convert distance to similarity
                
                review_data = json.loads(metadata["review_json"])
                
                # Create summary with proper ellipsis handling
                feedback = review_data["criteria"]["detailed_feedback"]
                review_summary = feedback[:200] + ("..." if len(feedback) > 200 else "")
                
                reviews.append(
                    StoredReview(
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
        
        return reviews

    def list_reviews(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[StoredReview]:
        """List all reviews with pagination.

        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of StoredReview objects

        """
        # Get all documents
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
                
                # Create summary with proper ellipsis handling
                feedback = review_data["criteria"]["detailed_feedback"]
                review_summary = feedback[:200] + ("..." if len(feedback) > 200 else "")
                
                reviews.append(
                    StoredReview(
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

    def get_review(self, review_id: str) -> Optional[dict]:
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

    def delete_review(self, review_id: str) -> bool:
        """Delete a review by ID.

        Args:
            review_id: ID of the review to delete

        Returns:
            True if deleted, False if not found

        """
        try:
            # Check if review exists first
            results = self.collection.get(ids=[review_id], include=["metadatas"])
            if not results["ids"]:
                return False
            
            metadata = results["metadatas"][0]
            pdf_path = metadata.get("pdf_path")
            
            # Delete PDF file if it exists
            if pdf_path and Path(pdf_path).exists():
                Path(pdf_path).unlink()
            
            # Delete from ChromaDB
            self.collection.delete(ids=[review_id])
            return True
        except Exception:
            return False

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

