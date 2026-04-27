import asyncio
import logging
import re
from typing import TYPE_CHECKING, cast

from decima import CustomLogger
from ollama import AsyncClient

if TYPE_CHECKING:
    from ollama import ListResponse

    from sibyl.storage.review import Review

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from sibyl.config import MAX_SCORE
from sibyl.routers.web_state import review_sessions, storage
from sibyl.web.model.search_request import SearchRequest
from sibyl.web.model.session_status import SessionStatus

router = APIRouter()

logger: CustomLogger = cast("CustomLogger", logging.getLogger(__name__))


@router.get("/session/{session_id}")
async def get_session_status(session_id: str) -> SessionStatus:
    """Get the status of a review session."""
    session = review_sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionStatus(
        session_id=session_id,
        status=session["status"],
        progress=session["progress"],
        message=session["message"],
        paper_title=session.get("paper_title"),
    )


@router.get("/health")
async def health_check() -> dict:
    """Check the health of the service."""
    try:
        return {
            "status": "healthy",
            "ollama_base_url": "OLLAMA_BASE_URL",
            "storage_count": storage.count_reviews(),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/config")
async def get_config() -> dict:
    """Get service configuration values."""
    return {"max_score": MAX_SCORE}


@router.post("/search")
async def search_reviews(request: SearchRequest) -> dict:
    """Search reviews using semantic similarity."""
    results: list[Review] = storage.search_reviews(request.query, limit=request.limit)
    return {
        "query": request.query,
        "results": [r.model_dump() for r in results],
        "count": len(results),
    }


@router.get("/reviews")
async def list_reviews(limit: int = 50, offset: int = 0, q: str | None = None) -> dict:
    """List all reviews with optional search filtering."""
    reviews: list[Review] = storage.list_reviews(limit=limit, offset=offset, search=q)
    total = storage.count_reviews()
    return {
        "reviews": [r.model_dump() for r in reviews],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/reviews/{review_id}")
async def get_review_details(review_id: str) -> dict:
    """Get the full details of a specific review."""
    review = storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.delete("/reviews")
async def delete_all_reviews() -> dict:
    """Delete all reviews from storage."""
    count = storage.delete_all_reviews()
    return {"message": f"Deleted {count} reviews", "count": count}


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: str) -> dict:
    """Delete a specific review by ID."""
    storage.delete_review(review_id)
    return {"message": "Review deleted successfully", "id": review_id}


@router.get("/statistics")
async def get_statistics() -> dict:
    """Get statistics about stored reviews."""
    return storage.get_statistics()


@router.get("/models")
async def list_models(request: Request) -> dict:
    """List models currently available in Ollama using the pre-instantiated client."""
    client: AsyncClient = request.app.state.ollama_clients[0]
    response: ListResponse = await client.list()

    return {
        "models": response.models,
        "count": len(response.models),
    }


@router.delete("/models/{model_name:path}")
async def delete_model(model_name: str, request: Request) -> dict:
    """Delete a model from Ollama."""
    client: AsyncClient = request.app.state.ollama_clients[0]
    try:
        await client.delete(model=model_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {e}") from e
    return {"message": f"Model '{model_name}' deleted successfully", "model": model_name}


@router.get("/models/available")
async def list_available_models(request: Request) -> dict:
    """List models available from the Ollama library."""
    try:
        process = await asyncio.create_subprocess_exec(
            "curl",
            "-s",
            "https://ollama.com/library",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=30)
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

    installed_model_names: set[str] = set()
    installed_variants_map: dict[str, list[str]] = {}

    client: AsyncClient = request.app.state.ollama_clients[0]
    response: ListResponse = await client.list()

    for model in response.models:
        model: ListResponse.Model
        full_name: str = model.model or ""
        base_name, _, tag = full_name.partition(":")
        if not tag:
            tag = "latest"
        if base_name:
            installed_variants_map.setdefault(base_name, []).append(tag)

    available_models = []
    for model_name in model_names:
        model_info = {
            "name": model_name,
            "description": "Available from Ollama library",
            "size": "Unknown",
            "installed": model_name in installed_model_names,
            "installed_variants": installed_variants_map.get(model_name, []),
        }
        available_models.append(model_info)

    return {"models": available_models, "count": len(available_models)}


@router.get("/models/available/{model_name}/tags")
async def get_model_tags(model_name: str) -> dict:
    """Fetch numerical size tags (e.g. 1.5b, 7b, 70b) for a specific Ollama library model."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"https://ollama.com/library/{model_name}")
            response.raise_for_status()
            html_content = response.text
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch model tags: {e}") from e

    raw_tags = re.findall(rf'href="/library/{re.escape(model_name)}:([^"]+)"', html_content)
    numerical_tags = sorted({tag for tag in raw_tags if re.fullmatch(r"\d+(\.\d+)?[bBmMkK]", tag)})

    return {"model": model_name, "tags": numerical_tags}


@router.get("/reviews/{review_id}/pdf")
async def download_review_pdf(review_id: str) -> FileResponse:
    """Download the original PDF for a review."""
    review = storage.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    pdf_path = review.get("pdf_path")
    if not isinstance(pdf_path, str) or not pdf_path:
        raise HTTPException(status_code=404, detail="PDF not available for this review")

    return FileResponse(pdf_path, media_type="application/pdf", filename=review.get("pdf_filename", "paper.pdf"))
