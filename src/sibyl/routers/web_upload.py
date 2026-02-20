"""Upload-related API routes."""

import tempfile
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile

from sibyl.routers.web_state import review_sessions

router = APIRouter()

_PDF_MAGIC = b"%PDF-"


def _validate_upload(file: UploadFile, content: bytes) -> None:
    """Validate that the uploaded file is a legitimate PDF.

    Args:
        file: The uploaded file object.
        content: Raw file bytes.

    Raises:
        HTTPException: If the file is not a valid PDF.

    """
    filename = file.filename or ""
    # Reject double extensions (e.g. malicious.pdf.exe)
    stem = Path(filename).stem
    if "." in stem:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if file.content_type not in ("application/pdf",):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    if not content.startswith(_PDF_MAGIC):
        raise HTTPException(status_code=400, detail="Invalid PDF file")


@router.post("/upload")
async def upload_paper(file: UploadFile) -> dict[str, str]:
    """Upload a PDF paper for review."""
    content = await file.read()

    _validate_upload(file, content)

    session_id = str(uuid.uuid4())

    temp_path: Path = Path(tempfile.gettempdir()) / f"{session_id}.pdf"

    async with aiofiles.open(temp_path, "wb") as f:
        await f.write(content)

    review_sessions[session_id] = {
        "status": "uploaded",
        "pdf_path": temp_path,
        "filename": file.filename,
        "progress": 0,
        "message": "File uploaded successfully",
    }

    return {"session_id": session_id, "filename": file.filename}
