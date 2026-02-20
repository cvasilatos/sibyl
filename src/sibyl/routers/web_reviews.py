import asyncio
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sibyl.storage.review import Review

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from sibyl.config import OLLAMA_BASE_URL
from sibyl.routers.web_state import review_sessions, storage
from sibyl.web.model.search_request import SearchRequest
from sibyl.web.model.session_status import SessionStatus

router = APIRouter()


@router.get("/session/{session_id}")
async def get_session_status(session_id: str) -> SessionStatus:
    session = review_sessions.get(session_id)
    return SessionStatus(
        session_id=session_id,
        status=session["status"],
        progress=session["progress"],
        message=session["message"],
        paper_title=session.get("paper_title"),
    )


@router.get("/health")
async def health_check() -> dict:
    try:
        return {
            "status": "healthy",
            "ollama_base_url": OLLAMA_BASE_URL,
            "storage_count": storage.count_reviews(),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.post("/search")
async def search_reviews(request: SearchRequest) -> dict:
    results: list[Review] = storage.search_reviews(request.query, limit=request.limit)
    return {
        "query": request.query,
        "results": [r.model_dump() for r in results],
        "count": len(results),
    }


@router.get("/reviews")
async def list_reviews(limit: int = 50, offset: int = 0) -> dict:
    reviews: list[Review] = storage.list_reviews(limit=limit, offset=offset)
    total = storage.count_reviews()
    return {
        "reviews": [r.model_dump() for r in reviews],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/reviews/{review_id}")
async def get_review_details(review_id: str):
    review = storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.delete("/reviews")
async def delete_all_reviews():
    count = storage.delete_all_reviews()
    return {"message": f"Deleted {count} reviews", "count": count}


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: str):
    storage.delete_review(review_id)
    return {"message": "Review deleted successfully", "id": review_id}


@router.get("/statistics")
async def get_statistics() -> dict:
    return storage.get_statistics()


@router.get("/models")
async def list_models():
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
        response.raise_for_status()

        models_data = response.json()
        return {
            "models": models_data.get("models", []),
            "count": len(models_data.get("models", [])),
        }


@router.get("/models/available")
async def list_available_models() -> dict:
    try:
        process = await asyncio.create_subprocess_exec(
            "curl",
            "-s",
            "https://ollama.com/library",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
        if process.returncode != 0:
            raise RuntimeError(f"curl failed with return code {process.returncode}")
        html_content = stdout.decode("utf-8")
    except (TimeoutError, RuntimeError, FileNotFoundError):
        async with httpx.AsyncClient(timeout=30.0) as client:
            library_response = await client.get("https://ollama.com/library")
            library_response.raise_for_status()
            html_content = library_response.text

    model_names = re.findall(r'href="/library/([^\"]+)', html_content)
    model_names = sorted(set(model_names))

    installed_models = set()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            models_data = response.json()
            installed_models = {m["name"].split(":")[0] for m in models_data.get("models", [])}
    except httpx.HTTPError:
        pass

    available_models = []
    for model_name in model_names:
        model_info = {
            "name": model_name,
            "description": "Available from Ollama library",
            "size": "Unknown",
            "installed": model_name in installed_models,
        }
        available_models.append(model_info)

    return {"models": available_models, "count": len(available_models)}


@router.get("/reviews/{review_id}/pdf")
async def download_review_pdf(review_id: str) -> FileResponse:
    review = storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    return FileResponse(review.get("pdf_path"), media_type="application/pdf", filename=review.get("pdf_filename", "paper.pdf"))
