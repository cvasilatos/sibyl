"""Response models for queued and running reviews."""

from typing import Literal

from pydantic import BaseModel, Field

from sibyl.schemas.ws import ReviewResults, ReviewStep

ReviewJobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
"""Where a review is: waiting for a GPU, running, or finished one way or another."""

ACTIVE_STATUSES: frozenset[str] = frozenset({"queued", "running"})


class ReviewJob(BaseModel):
    """A review submitted to the queue. It runs on the server whether or not anyone has the page open."""

    id: str
    owner: str
    """Username of who submitted it; only they (and admins) may cancel it."""
    filename: str
    model: str
    form_name: str | None = None
    """The conference template or custom form the review answers; None for the generic review."""
    status: ReviewJobStatus
    position: int | None = None
    """Place in the queue (1 = next to start) while queued; None otherwise."""
    requested_gpu: int | None = None
    """GPU the user asked for; None lets the queue use the first free one."""
    gpu: int | None = None
    """GPU it runs (or ran) on; None before it starts or on a machine without GPUs Sibyl schedules."""
    steps: list[ReviewStep] = []
    """The steps this review takes, in order."""
    step: ReviewStep | None = None
    """The step in progress (or the one that failed)."""
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    review_id: str | None = None
    """The saved review, once completed."""
    results: ReviewResults | None = None


class ReviewJobList(BaseModel):
    """Every queued and running review (anyone's), and the signed-in user's finished ones."""

    jobs: list[ReviewJob]
    slots: int
    """How many reviews run at once (one per GPU)."""
