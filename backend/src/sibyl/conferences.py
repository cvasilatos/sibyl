"""Official reviewer forms of top conferences, turned into structured, schema-enforced review templates.

Each template lives in ``sibyl/resources/conferences/<id>.json``. Every question becomes a required field in
the JSON schema sent to the model, and score questions are restricted to the conference's own scale, so even
small models must answer every question with a valid value.
"""

from __future__ import annotations

import functools
import importlib.resources as pkg_resources
import json
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

AREA_ORDER = ["Machine Learning", "Computer Vision", "Natural Language Processing", "Data Mining", "Security", "Design Automation"]


class ChoiceOption(BaseModel):
    """One level of a rating scale."""

    value: int | str
    label: str


class Question(BaseModel):
    """A single question of a reviewer form."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    type: Literal["text", "choice"]
    prompt: str = ""
    options: list[ChoiceOption] = Field(default_factory=list)

    @model_validator(mode="after")
    def _choices_have_options(self) -> Question:
        if self.type == "choice" and not self.options:
            raise ValueError(f"choice question '{self.id}' needs options")
        return self

    def option_label(self, value: int | str) -> str | None:
        """Return the label for a scale value."""
        return next((o.label for o in self.options if str(o.value) == str(value)), None)


class ConferenceTemplate(BaseModel):
    """A conference's reviewer form."""

    id: str
    name: str
    full_name: str
    area: str
    edition: str
    source_urls: list[str] = Field(default_factory=list)
    verified: bool = False
    notes: str = ""
    guidelines: str = ""
    questions: list[Question]

    @model_validator(mode="after")
    def _unique_ids(self) -> ConferenceTemplate:
        ids = [q.id for q in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{self.id}: duplicate question ids")
        return self

    def summary(self) -> dict[str, Any]:
        """Short description for listings."""
        return self.model_dump(include={"id", "name", "full_name", "area", "edition", "verified", "source_urls"}) | {"question_count": len(self.questions)}

    def json_schema(self) -> dict[str, Any]:
        """JSON schema forcing one answer per question, with scores restricted to the official scale."""
        properties: dict[str, Any] = {}
        for q in self.questions:
            description = f"{q.label}. {q.prompt}".strip()
            if q.type == "choice":
                scale = "; ".join(f"{o.value} = {o.label}" for o in q.options)
                values = [o.value for o in q.options]
                value_type = "integer" if all(isinstance(v, int) for v in values) else "string"
                properties[q.id] = {"type": value_type, "enum": values, "description": f"{description} Scale: {scale}"}
            else:
                properties[q.id] = {"type": "string", "minLength": 1, "description": description}
        return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}

    def prompt_text(self) -> str:
        """Human-readable form included in the prompt so the model sees each question's full instructions."""
        lines = [f"# {self.name} {self.edition} reviewer form ({self.full_name})"]
        if self.guidelines:
            lines += ["", "Reviewer guidelines:", self.guidelines]
        for q in self.questions:
            lines += ["", f"## {q.label} (field `{q.id}`)"]
            if q.prompt:
                lines.append(q.prompt)
            lines += [f"- {o.value}: {o.label}" for o in q.options]
        return "\n".join(lines)

    def normalize_answers(self, answers: dict[str, Any]) -> dict[str, int | str]:
        """Validate model answers against the form, coercing numeric strings on numeric scales."""
        normalized: dict[str, int | str] = {}
        missing = [q.id for q in self.questions if q.id not in answers]
        if missing:
            raise ValueError(f"Review is missing answers for: {', '.join(missing)}")
        for q in self.questions:
            value = answers[q.id]
            if q.type == "choice":
                match = next((o.value for o in q.options if str(o.value) == str(value).strip()), None)
                if match is None:
                    raise ValueError(f"'{value}' is not a valid answer for {q.label}")
                normalized[q.id] = match
            else:
                normalized[q.id] = str(value).strip()
        return normalized

    def render_markdown(self, answers: dict[str, int | str]) -> str:
        """Render a completed form as Markdown, in the official order."""
        parts = [f"# {self.name} {self.edition} Review"]
        for q in self.questions:
            value = answers.get(q.id, "")
            if q.type == "choice":
                parts.append(f"**{q.label}:** {value} — {q.option_label(value) or ''}".rstrip(" —"))
            else:
                parts.append(f"## {q.label}\n\n{value}")
        return "\n\n".join(parts)


@functools.cache
def load_conferences() -> dict[str, ConferenceTemplate]:
    """Load all bundled conference templates, keyed by id."""
    directory = pkg_resources.files("sibyl.resources") / "conferences"
    templates: dict[str, ConferenceTemplate] = {}
    if not directory.is_dir():
        return templates
    for entry in sorted(directory.iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".json"):
            template = ConferenceTemplate.model_validate(json.loads(entry.read_text(encoding="utf-8")))
            templates[template.id] = template
    return templates


def get_conference(conference_id: str) -> ConferenceTemplate | None:
    """Return a template by id."""
    return load_conferences().get(conference_id)


def list_conferences() -> list[dict[str, Any]]:
    """Summaries sorted by research area, then name."""

    def area_rank(area: str) -> int:
        return AREA_ORDER.index(area) if area in AREA_ORDER else len(AREA_ORDER)

    return [t.summary() for t in sorted(load_conferences().values(), key=lambda t: (area_rank(t.area), t.name.lower()))]
