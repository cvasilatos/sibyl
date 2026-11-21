"""Response models for stored reviews."""

from pydantic import BaseModel

from sibyl.storage.review import Review


class ReviewCriteria(BaseModel):
    """A review's assessment, as stored. Loosely typed so reviews saved by older versions still load."""

    novelty: str = ""
    methodology: str = ""
    results: str = ""
    clarity: str = ""
    impact: str = ""
    limitations: str = ""
    strengths: str = ""
    score: int = 0
    recommendation: str = ""
    detailed_feedback: str = ""
    review_form_response: str | None = None
    conference: str | None = None
    review_form_answers: dict[str, int | str] | None = None


class FullReview(BaseModel):
    """A stored review with its full criteria and the model's raw output."""

    id: str
    paper_title: str
    pdf_filename: str
    pdf_path: str | None
    reviewer_model: str
    score: int
    recommendation: str
    created_at: str
    criteria: ReviewCriteria
    raw_response: str


class ReviewList(BaseModel):
    """One page of stored reviews."""

    reviews: list[Review]
    total: int
    limit: int
    offset: int


class SearchResults(BaseModel):
    """Reviews ranked by semantic similarity to a query."""

    query: str
    results: list[Review]
    count: int


class ReviewStatistics(BaseModel):
    """Aggregate counts over all stored reviews."""

    total_reviews: int
    unique_papers: int
    unique_models: int
    recommendations: dict[str, int]


class DeletedReview(BaseModel):
    """Result of deleting one review."""

    message: str
    id: str


class DeletedReviews(BaseModel):
    """Result of deleting all reviews."""

    message: str
    count: int
