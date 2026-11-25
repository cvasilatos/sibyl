from pydantic import BaseModel


class Review(BaseModel):
    """Model for a stored review with metadata."""

    id: str
    paper_title: str
    pdf_filename: str
    pdf_path: str | None = None
    reviewer_model: str
    score: int
    recommendation: str
    review_summary: str
    created_at: str
    similarity_score: float | None = None
    owner: str | None = None
    """Username of who ran the review; None for reviews saved before Sibyl had users."""
