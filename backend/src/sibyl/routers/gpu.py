"""GPU monitoring endpoints (NVIDIA via NVML, Apple Silicon via ioreg)."""

from fastapi import APIRouter, HTTPException

from sibyl.services import hardware

router = APIRouter()


@router.get("/gpu")
async def list_gpus() -> dict:
    """List all available GPUs with their current stats."""
    try:
        return hardware.list_gpus()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"GPU monitoring unavailable: {e}") from e


@router.get("/gpu/{gpu_index}")
async def get_gpu(gpu_index: int) -> dict:
    """Get stats for a specific GPU by index."""
    data = await list_gpus()
    if not data["available"]:
        raise HTTPException(status_code=503, detail="GPU monitoring unavailable on this machine")
    for gpu in data["gpus"]:
        if gpu["index"] == gpu_index:
            return gpu
    raise HTTPException(status_code=404, detail=f"GPU index {gpu_index} not found (count={data['count']})")
