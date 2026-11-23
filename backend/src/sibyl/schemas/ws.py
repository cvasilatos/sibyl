"""Messages sent over the WebSocket endpoints.

OpenAPI does not describe WebSockets, so ``sibyl.main`` adds these models to the exported schema by hand
(``WS_MESSAGES``); the web app's types are generated from them like any response model.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from sibyl.schemas.related_work import RelatedPaper
from sibyl.schemas.review_config import ReviewConfig
from sibyl.schemas.reviews import ReviewCriteria


class SocketError(BaseModel):
    """Final message when a WebSocket operation fails."""

    status: Literal["error"] = "error"
    message: str


class ReviewResult(BaseModel):
    """One model's review of the paper, as sent when the review completes."""

    paper_title: str
    reviewer_model: str
    criteria: ReviewCriteria
    raw_response: str
    related_work: list[RelatedPaper] = []
    config: ReviewConfig | None = None


class ReviewResults(BaseModel):
    """The reviews produced by a review session."""

    paper_title: str
    reviews: list[ReviewResult]


class ReviewProgress(BaseModel):
    """A step of a running review."""

    status: Literal["progress"] = "progress"
    progress: int = Field(ge=0, le=100)
    message: str


class ReviewCompleted(BaseModel):
    """Final message of a successful review."""

    status: Literal["completed"] = "completed"
    progress: int = 100
    message: str = "Review complete!"
    review_id: str
    results: ReviewResults


ReviewSessionMessage = Annotated[ReviewProgress | ReviewCompleted | SocketError, Field(discriminator="status")]
"""Anything sent on ``/ws/session/{session_id}``."""


class PullProgress(BaseModel):
    """A progress line from the engine while it downloads a model; the last one has status ``success``.

    Engines may add their own fields (Ollama sends ``digest``), which are passed through.
    """

    model_config = ConfigDict(extra="allow")

    status: str
    completed: int | None = None
    total: int | None = None


WS_MESSAGES: tuple[type[BaseModel], ...] = (ReviewProgress, ReviewCompleted, SocketError, PullProgress)
"""Models added to the OpenAPI schema so clients can type WebSocket messages."""
