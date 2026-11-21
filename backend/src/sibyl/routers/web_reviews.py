import logging
import platform
from typing import TYPE_CHECKING, cast

from decima import CustomLogger

if TYPE_CHECKING:
    from sibyl.inference import InferenceEngine
    from sibyl.storage.review import Review

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from sibyl.config import MAX_SCORE
from sibyl.inference import EngineOperationNotSupportedError
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
    if not storage.delete_review(review_id):
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted successfully", "id": review_id}


@router.get("/statistics")
async def get_statistics() -> dict:
    """Get statistics about stored reviews."""
    return storage.get_statistics()


@router.get("/engine")
async def engine_info(request: Request) -> dict:
    """Describe the active inference engine and platform."""
    engine: InferenceEngine = request.app.state.engine
    return {**engine.info(), "platform": platform.system().lower(), "machine": platform.machine()}


@router.get("/models")
async def list_models(request: Request) -> dict:
    """List models installed in the active inference engine."""
    engine: InferenceEngine = request.app.state.engine
    try:
        models = await engine.list_installed()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach the {engine.label} backend: {e}") from e
    return {"models": models, "count": len(models)}


@router.delete("/models/{model_name:path}")
async def delete_model(model_name: str, request: Request) -> dict:
    """Delete a downloaded model."""
    engine: InferenceEngine = request.app.state.engine
    try:
        await engine.delete(model_name)
    except EngineOperationNotSupportedError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {e}") from e
    return {"message": f"Model '{model_name}' deleted successfully", "model": model_name}


@router.get("/models/available")
async def list_available_models(request: Request) -> dict:
    """List models that can be downloaded through the active engine."""
    engine: InferenceEngine = request.app.state.engine
    try:
        available_models = await engine.list_catalog()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch model catalog: {e}") from e

    return {"models": available_models, "count": len(available_models)}


@router.get("/models/available/{model_name:path}/tags")
async def get_model_tags(model_name: str, request: Request) -> dict:
    """Fetch downloadable size variants (e.g. 1.5b, 7b, 70b) for a catalog model."""
    engine: InferenceEngine = request.app.state.engine
    try:
        tags = await engine.list_variants(model_name)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch model tags: {e}") from e

    return {"model": model_name, "tags": tags}


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
