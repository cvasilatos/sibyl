"""Response models for saved custom review forms."""

from pydantic import BaseModel


class SavedFormSummary(BaseModel):
    """A saved review form, without its text."""

    id: str
    name: str
    filename: str
    created_at: str
    size: int
    owner: str | None = None


class SavedFormList(BaseModel):
    """All saved review forms."""

    forms: list[SavedFormSummary]
    count: int


class SavedFormDetail(BaseModel):
    """A saved review form with its text."""

    id: str
    name: str
    filename: str
    created_at: str
    content: str
    owner: str | None = None


class DeletedForm(BaseModel):
    """Confirmation of a deleted review form."""

    message: str
    id: str
