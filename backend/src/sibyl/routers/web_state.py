"""Shared state for web modules."""

from pathlib import Path
from typing import Any, TypedDict

from sibyl.storage.engine import Engine


class ReviewSession(TypedDict, total=False):
    """State tracked for one uploaded-paper review workflow."""

    status: str
    pdf_path: Path
    filename: str | None
    progress: int
    message: str
    paper_title: str
    reviews: list[dict[str, Any]]


review_sessions: dict[str, ReviewSession] = {}

storage = Engine()
