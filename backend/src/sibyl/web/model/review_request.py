from pydantic import BaseModel


class ReviewRequest(BaseModel):
    """Request model for initiating a paper review."""

    model_name: str | None = None
    max_pages: int | None = None
