from pydantic import BaseModel


class SessionStatus(BaseModel):
    """Status model for a review session."""

    session_id: str
    status: str
    progress: int
    message: str
    paper_title: str | None = None
