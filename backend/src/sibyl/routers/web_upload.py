"""Upload-related API routes."""

import tempfile
import uuid
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile

from sibyl.routers.web_state import review_sessions

router = APIRouter()

MAX_REVIEW_FORM_BYTES = 64 * 1024
REVIEW_FORM_EXTENSIONS = {".txt", ".md", ".markdown"}


def _decode_review_form(filename: str, content: bytes) -> str:
    """Validate and decode a text or Markdown review form."""
    if Path(filename).suffix.lower() not in REVIEW_FORM_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Review form must be a .txt, .md, or .markdown file")
    if len(content) > MAX_REVIEW_FORM_BYTES:
        raise HTTPException(status_code=413, detail="Review form must be 64 KiB or smaller")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Review form must contain valid UTF-8 text") from exc
    if not decoded.strip():
        raise HTTPException(status_code=400, detail="Review form cannot be empty")
    return decoded


@router.post("/upload")
async def upload_paper(file: UploadFile, review_form: UploadFile | None = None) -> dict[str, Any]:
    """Upload a PDF paper and an optional UTF-8 text/Markdown review form."""
    content = await file.read()

    review_form_content: str | None = None
    review_form_filename: str | None = None
    if review_form is not None:
        review_form_filename = review_form.filename or ""
        form_bytes = await review_form.read(MAX_REVIEW_FORM_BYTES + 1)
        review_form_content = _decode_review_form(review_form_filename, form_bytes)

    session_id = str(uuid.uuid4())

    temp_path: Path = Path(tempfile.gettempdir()) / f"{session_id}.pdf"

    async with aiofiles.open(temp_path, "wb") as f:
        await f.write(content)

    review_sessions[session_id] = {
        "status": "uploaded",
        "pdf_path": temp_path,
        "filename": file.filename,
        "review_form": review_form_content,
        "review_form_filename": review_form_filename,
        "progress": 0,
        "message": "File uploaded successfully",
    }

    return {
        "session_id": session_id,
        "filename": file.filename,
        "review_form_filename": review_form_filename,
    }
