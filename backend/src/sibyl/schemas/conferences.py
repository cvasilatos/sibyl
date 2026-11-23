"""Response models for conference review templates."""

from pydantic import BaseModel

from sibyl.services.conferences import ConferenceTemplate, PageLimit


class ConferenceSummary(BaseModel):
    """A conference template, without its questions."""

    id: str
    name: str
    full_name: str
    area: str
    edition: str
    verified: bool
    source_urls: list[str]
    page_limit: PageLimit | None
    question_count: int


class ConferenceList(BaseModel):
    """All bundled conference templates."""

    conferences: list[ConferenceSummary]
    count: int


class ConferenceDetail(ConferenceTemplate):
    """A conference template with its questions and the form rendered as Markdown."""

    form_markdown: str
