"""Response models for service status, configuration and uploads."""

from pydantic import BaseModel


class Health(BaseModel):
    """Service health. ``storage_count`` is set when healthy, ``error`` when not."""

    status: str
    storage_count: int | None = None
    error: str | None = None


class ServiceConfig(BaseModel):
    """Configuration values the frontend needs."""

    max_score: int


class Online(BaseModel):
    """Root liveness check."""

    status: str
    system: str


class UploadResult(BaseModel):
    """A paper uploaded and waiting for review."""

    session_id: str
    filename: str | None
    review_form_filename: str | None
    conference_id: str | None
