"""Response models for service status and configuration."""

from pydantic import BaseModel

from sibyl.schemas.review_config import ReviewDetail, ReviewMode


class Health(BaseModel):
    """Service health. ``storage_count`` is set when healthy, ``error`` when not."""

    status: str
    storage_count: int | None = None
    error: str | None = None


class ServiceConfig(BaseModel):
    """Configuration values the frontend needs."""

    max_score: int
    review_detail: ReviewDetail
    """Default review length (``SIBYL_REVIEW_DETAIL``)."""
    review_mode: ReviewMode
    """Default generation mode (``SIBYL_REVIEW_MODE``)."""


class Online(BaseModel):
    """Root liveness check."""

    status: str
    system: str
