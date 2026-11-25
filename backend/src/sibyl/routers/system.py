"""Endpoints that work without signing in: service health and the configuration the sign-in page needs."""

from fastapi import APIRouter

from sibyl.config import MAX_SCORE
from sibyl.schemas.system import Health, ServiceConfig
from sibyl.services.reviewer import DEFAULT_DETAIL, DEFAULT_MODE
from sibyl.state import storage

router = APIRouter()


@router.get("/health", response_model_exclude_none=True)
async def health_check() -> Health:
    """Check the health of the service."""
    try:
        return Health(status="healthy", storage_count=storage.count_reviews())
    except Exception as e:
        return Health(status="unhealthy", error=str(e))


@router.get("/config")
async def get_config() -> ServiceConfig:
    """Get service configuration values."""
    return ServiceConfig(max_score=MAX_SCORE, review_detail=DEFAULT_DETAIL, review_mode=DEFAULT_MODE)
