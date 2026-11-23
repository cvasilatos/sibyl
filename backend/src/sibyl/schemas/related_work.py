"""A related paper found on arXiv, as shown to the reviewer and returned with the review."""

from pydantic import BaseModel, Field


class RelatedPaper(BaseModel):
    """A paper found on arXiv and judged relevant to the submission."""

    ref: str = Field(description="Citation key used in the review, e.g. R1")
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    url: str
    abstract: str = ""
    relation: str = Field(default="", description="How the paper relates to the submission, written by the model")
