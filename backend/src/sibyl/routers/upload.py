"""Upload-related API routes."""

import tempfile
import uuid
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Form, HTTPException, UploadFile

from sibyl.schemas.system import UploadResult
from sibyl.services.conferences import get_conference
from sibyl.services.review_forms import MAX_REVIEW_FORM_BYTES, ReviewFormError, decode_review_form, get_form
from sibyl.state import review_sessions

router = APIRouter()


def _decode_review_form(filename: str, content: bytes) -> str:
    """Validate and decode a text or Markdown review form."""
    try:
        return decode_review_form(filename, content)
    except ReviewFormError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e


@router.post("/upload")
async def upload_paper(
    file: UploadFile,
    review_form: UploadFile | None = None,
    conference_id: Annotated[str | None, Form()] = None,
    review_form_id: Annotated[str | None, Form()] = None,
) -> UploadResult:
    """Upload a PDF paper with at most one review form: a conference template, a saved form, or a UTF-8 text/Markdown file."""
    conference_id = conference_id or None
    review_form_id = review_form_id or None
    if sum(x is not None for x in (conference_id, review_form_id, review_form)) > 1:
        raise HTTPException(status_code=400, detail="Choose only one review form: a conference template, a saved form, or an uploaded file")
    if conference_id is not None and get_conference(conference_id) is None:
        raise HTTPException(status_code=400, detail=f"Unknown conference template '{conference_id}'")

    content = await file.read()

    review_form_content: str | None = None
    review_form_filename: str | None = None
    if review_form is not None:
        review_form_filename = review_form.filename or ""
        form_bytes = await review_form.read(MAX_REVIEW_FORM_BYTES + 1)
        review_form_content = _decode_review_form(review_form_filename, form_bytes)
    elif review_form_id is not None:
        saved = get_form(review_form_id)
        if saved is None:
            raise HTTPException(status_code=400, detail="Unknown saved review form")
        review_form_content, review_form_filename = saved.content, saved.name

    session_id = str(uuid.uuid4())

    temp_path: Path = Path(tempfile.gettempdir()) / f"{session_id}.pdf"

    async with aiofiles.open(temp_path, "wb") as f:
        await f.write(content)

    review_sessions[session_id] = {
        "status": "uploaded",
        "pdf_path": temp_path,
        "filename": file.filename or "paper.pdf",  # the stored review needs a name even if the client sent none
        "review_form": review_form_content,
        "review_form_filename": review_form_filename,
        "conference_id": conference_id,
        "progress": 0,
        "message": "File uploaded successfully",
    }

    return UploadResult(session_id=session_id, filename=file.filename, review_form_filename=review_form_filename, conference_id=conference_id)
