from pydantic import BaseModel


class ReviewRequest(BaseModel):
    model_name: str | None = None
    max_pages: int | None = None
