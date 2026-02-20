"""Upload-related API routes."""

import tempfile
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, UploadFile

from sibyl.routers.web_state import review_sessions

router = APIRouter()


@router.post("/upload")
async def upload_paper(file: UploadFile) -> dict[str, str]:
    """Upload a PDF paper for review."""
    content = await file.read()

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
