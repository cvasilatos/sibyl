"""Storage module for persisting and searching reviews and PDFs."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from .reviewer import PaperReview


class StoredReview(BaseModel):
    """Model for a stored review with metadata."""

    id: int
    paper_title: str
    pdf_filename: str
    pdf_path: Optional[str] = None
    reviewer_model: str
    overall_score: int
    recommendation: str
    review_data: str  # JSON string of complete review
    created_at: str
    paper_text: Optional[str] = None


class ReviewStorage:
    """SQLite-based storage for reviews with full-text search."""

    def __init__(self, db_path: str = "sibyl_reviews.db"):
        """Initialize the storage system.

        Args:
            db_path: Path to the SQLite database file

        """
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_title TEXT NOT NULL,
                pdf_filename TEXT NOT NULL,
                pdf_path TEXT,
                reviewer_model TEXT NOT NULL,
                overall_score INTEGER NOT NULL,
                recommendation TEXT NOT NULL,
                review_data TEXT NOT NULL,
                paper_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create full-text search virtual table
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS reviews_fts USING fts5(
                paper_title,
                reviewer_model,
                recommendation,
                review_content,
                paper_text,
                content=reviews,
                content_rowid=id
            )
        """)

        # Create triggers to keep FTS table in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS reviews_ai AFTER INSERT ON reviews BEGIN
                INSERT INTO reviews_fts(
                    rowid,
                    paper_title,
                    reviewer_model,
                    recommendation,
                    review_content,
                    paper_text
                )
                VALUES (
                    new.id,
                    new.paper_title,
                    new.reviewer_model,
                    new.recommendation,
                    new.review_data,
                    COALESCE(new.paper_text, '')
                );
            END;
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS reviews_ad AFTER DELETE ON reviews BEGIN
                INSERT INTO reviews_fts(
                    reviews_fts,
                    rowid,
                    paper_title,
                    reviewer_model,
                    recommendation,
                    review_content,
                    paper_text
                )
                VALUES (
                    'delete',
                    old.id,
                    old.paper_title,
                    old.reviewer_model,
                    old.recommendation,
                    old.review_data,
                    COALESCE(old.paper_text, '')
                );
            END;
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS reviews_au AFTER UPDATE ON reviews BEGIN
                INSERT INTO reviews_fts(
                    reviews_fts,
                    rowid,
                    paper_title,
                    reviewer_model,
                    recommendation,
                    review_content,
                    paper_text
                )
                VALUES (
                    'delete',
                    old.id,
                    old.paper_title,
                    old.reviewer_model,
                    old.recommendation,
                    old.review_data,
                    COALESCE(old.paper_text, '')
                );
                INSERT INTO reviews_fts(
                    rowid,
                    paper_title,
                    reviewer_model,
                    recommendation,
                    review_content,
                    paper_text
                )
                VALUES (
                    new.id,
                    new.paper_title,
                    new.reviewer_model,
                    new.recommendation,
                    new.review_data,
                    COALESCE(new.paper_text, '')
                );
            END;
        """)

        conn.commit()
        conn.close()

    def save_review(
        self,
        review: PaperReview,
        pdf_filename: str,
        pdf_path: Optional[str] = None,
        paper_text: Optional[str] = None,
    ) -> int:
        """Save a review to the database.

        Args:
            review: The PaperReview object to save
            pdf_filename: Original filename of the PDF
            pdf_path: Optional path to the stored PDF file
            paper_text: Optional full text of the paper for search

        Returns:
            ID of the saved review

        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        review_data = json.dumps(
            {
                "paper_title": review.paper_title,
                "reviewer_model": review.reviewer_model,
                "criteria": review.criteria.model_dump(),
                "raw_response": review.raw_response,
            }
        )

        cursor.execute(
            """
            INSERT INTO reviews (
                paper_title,
                pdf_filename,
                pdf_path,
                reviewer_model,
                overall_score,
                recommendation,
                review_data,
                paper_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                review.paper_title,
                pdf_filename,
                pdf_path,
                review.reviewer_model,
                review.criteria.overall_score,
                review.criteria.recommendation,
                review_data,
                paper_text,
            ),
        )

        review_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return review_id

    def search_reviews(
        self, query: str, limit: int = 50
    ) -> List[StoredReview]:
        """Search reviews using full-text search.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of matching StoredReview objects

        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT r.*
            FROM reviews r
            INNER JOIN reviews_fts fts ON r.id = fts.rowid
            WHERE reviews_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """,
            (query, limit),
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                StoredReview(
                    id=row["id"],
                    paper_title=row["paper_title"],
                    pdf_filename=row["pdf_filename"],
                    pdf_path=row["pdf_path"],
                    reviewer_model=row["reviewer_model"],
                    overall_score=row["overall_score"],
                    recommendation=row["recommendation"],
                    review_data=row["review_data"],
                    created_at=row["created_at"],
                )
            )

        conn.close()
        return results

    def list_reviews(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at DESC",
    ) -> List[StoredReview]:
        """List all reviews with pagination.

        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip
            order_by: SQL ORDER BY clause (default: newest first)

        Returns:
            List of StoredReview objects

        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Validate order_by to prevent SQL injection
        allowed_orders = [
            "created_at DESC",
            "created_at ASC",
            "overall_score DESC",
            "overall_score ASC",
            "paper_title ASC",
            "paper_title DESC",
        ]
        if order_by not in allowed_orders:
            order_by = "created_at DESC"

        cursor.execute(
            f"""
            SELECT * FROM reviews
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )

        results = []
        for row in cursor.fetchall():
            results.append(
                StoredReview(
                    id=row["id"],
                    paper_title=row["paper_title"],
                    pdf_filename=row["pdf_filename"],
                    pdf_path=row["pdf_path"],
                    reviewer_model=row["reviewer_model"],
                    overall_score=row["overall_score"],
                    recommendation=row["recommendation"],
                    review_data=row["review_data"],
                    created_at=row["created_at"],
                )
            )

        conn.close()
        return results

    def get_review(self, review_id: int) -> Optional[StoredReview]:
        """Get a specific review by ID.

        Args:
            review_id: ID of the review to retrieve

        Returns:
            StoredReview object or None if not found

        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM reviews WHERE id = ?", (review_id,))
        row = cursor.fetchone()

        result = None
        if row:
            result = StoredReview(
                id=row["id"],
                paper_title=row["paper_title"],
                pdf_filename=row["pdf_filename"],
                pdf_path=row["pdf_path"],
                reviewer_model=row["reviewer_model"],
                overall_score=row["overall_score"],
                recommendation=row["recommendation"],
                review_data=row["review_data"],
                created_at=row["created_at"],
                paper_text=row["paper_text"],
            )

        conn.close()
        return result

    def delete_review(self, review_id: int) -> bool:
        """Delete a review by ID.

        Args:
            review_id: ID of the review to delete

        Returns:
            True if deleted, False if not found

        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def count_reviews(self) -> int:
        """Get the total number of reviews in storage.

        Returns:
            Total count of reviews

        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM reviews")
        count = cursor.fetchone()[0]

        conn.close()
        return count

    def get_statistics(self) -> dict:
        """Get statistics about stored reviews.

        Returns:
            Dictionary with statistics

        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get overall statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_reviews,
                AVG(overall_score) as avg_score,
                MIN(overall_score) as min_score,
                MAX(overall_score) as max_score,
                COUNT(DISTINCT paper_title) as unique_papers,
                COUNT(DISTINCT reviewer_model) as unique_models
            FROM reviews
        """)
        stats = dict(cursor.fetchone())

        # Get recommendation distribution
        cursor.execute("""
            SELECT recommendation, COUNT(*) as count
            FROM reviews
            GROUP BY recommendation
        """)
        stats["recommendations"] = {
            row["recommendation"]: row["count"] for row in cursor.fetchall()
        }

        conn.close()
        return stats
