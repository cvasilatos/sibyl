from pydantic import BaseModel


class ReviewResponse(BaseModel):
    session_id: str
    paper_title: str
    reviews: list[dict]
    comparison: dict
