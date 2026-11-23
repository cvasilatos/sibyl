"""Response models for saved custom review forms."""

from pydantic import BaseModel


class SavedFormSummary(BaseModel):
    """A saved review form, without its text."""

    id: str
    name: str
    filename: str
    created_at: str
    size: int


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


class DeletedForm(BaseModel):
    """Confirmation of a deleted review form."""

    message: str
    id: str
