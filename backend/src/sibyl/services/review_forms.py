"""Custom reviewer forms that users upload and name, saved so they can be reused across reviews.

Each form is one JSON file in ``<SIBYL_STORAGE_PATH>/review_forms/<id>.json`` holding its name, the original file
name and the form text.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from sibyl import config

MAX_REVIEW_FORM_BYTES = 64 * 1024
REVIEW_FORM_EXTENSIONS = {".txt", ".md", ".markdown"}
MAX_NAME_LENGTH = 100


class ReviewFormError(ValueError):
    """A form or name that cannot be saved, with the HTTP status that describes why."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        """Keep the message and the HTTP status to answer with."""
        super().__init__(message)
        self.status_code = status_code


class SavedForm(BaseModel):
    """A named custom reviewer form."""

    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    name: str
    filename: str
    created_at: str
    content: str

    def summary(self) -> dict[str, str | int]:
        """Short description for listings."""
        return self.model_dump(exclude={"content"}) | {"size": len(self.content.encode())}


def forms_dir() -> Path:
    """Directory holding saved forms; read on each call so tests can point ``config.STORAGE_PATH`` elsewhere."""
    return config.STORAGE_PATH / "review_forms"


def decode_review_form(filename: str, content: bytes) -> str:
    """Validate and decode a text or Markdown review form."""
    if Path(filename).suffix.lower() not in REVIEW_FORM_EXTENSIONS:
        raise ReviewFormError("Review form must be a .txt, .md, or .markdown file")
    if len(content) > MAX_REVIEW_FORM_BYTES:
        raise ReviewFormError("Review form must be 64 KiB or smaller", status_code=413)
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ReviewFormError("Review form must contain valid UTF-8 text") from exc
    if not decoded.strip():
        raise ReviewFormError("Review form cannot be empty")
    return decoded


def _path(form_id: str) -> Path | None:
    """File of a form id, or None for an id that is not one of ours (so ids never escape the directory)."""
    return forms_dir() / f"{form_id}.json" if re.fullmatch(r"[0-9a-f]{32}", form_id) else None


def list_forms() -> list[SavedForm]:
    """All saved forms, sorted by name."""
    directory = forms_dir()
    if not directory.is_dir():
        return []
    forms = [SavedForm.model_validate_json(path.read_text(encoding="utf-8")) for path in directory.glob("*.json")]
    return sorted(forms, key=lambda f: f.name.lower())


def get_form(form_id: str) -> SavedForm | None:
    """Return a saved form by id."""
    path = _path(form_id)
    if path is None or not path.is_file():
        return None
    return SavedForm.model_validate_json(path.read_text(encoding="utf-8"))


def save_form(name: str, filename: str, content: str) -> SavedForm:
    """Save a decoded form under a name no other saved form uses."""
    name = " ".join(name.split())
    if not name:
        raise ReviewFormError("Give the review form a name")
    if len(name) > MAX_NAME_LENGTH:
        raise ReviewFormError(f"The name must be {MAX_NAME_LENGTH} characters or fewer")
    if any(f.name.lower() == name.lower() for f in list_forms()):
        raise ReviewFormError(f"A review form named '{name}' already exists", status_code=409)
    form = SavedForm(id=uuid.uuid4().hex, name=name, filename=filename, created_at=datetime.now(UTC).isoformat(), content=content)
    directory = forms_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{form.id}.json").write_text(json.dumps(form.model_dump(), indent=2), encoding="utf-8")
    return form


def delete_form(form_id: str) -> bool:
    """Delete a saved form; False when there is none with that id."""
    path = _path(form_id)
    if path is None or not path.is_file():
        return False
    path.unlink()
    return True
