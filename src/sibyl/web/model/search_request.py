from pydantic import BaseModel


class SearchRequest(BaseModel):
    """Request model for semantic review search."""

    query: str
    limit: int = 10
