from pydantic import BaseModel


class SessionStatus(BaseModel):
    session_id: str
    status: str
    progress: int
    message: str
    paper_title: str | None = None
    results: dict | None = None
