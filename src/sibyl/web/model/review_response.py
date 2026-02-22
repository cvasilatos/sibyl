from pydantic import BaseModel


class ReviewResponse(BaseModel):
    """Response model for a completed paper review."""

    session_id: str
    paper_title: str
    reviews: list[dict]
    comparison: dict
