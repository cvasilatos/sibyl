"""GPU monitoring endpoints."""

import contextlib

from fastapi import APIRouter, HTTPException

try:
    import pynvml

    pynvml.nvmlInit()
    _NVML_AVAILABLE = True
except Exception:
    _NVML_AVAILABLE = False

router = APIRouter()


def _get_gpu_info(index: int) -> dict:
    """Return stats for a single GPU by index."""
    handle = pynvml.nvmlDeviceGetHandleByIndex(index)

    name: str = pynvml.nvmlDeviceGetName(handle)
    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)

    temperature: int | None = None
    with contextlib.suppress(pynvml.NVMLError):
        temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

    power_usage: float | None = None
    power_limit: float | None = None
    try:
        power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
        power_limit = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000.0
    except pynvml.NVMLError:
        pass

    fan_speed: int | None = None
    with contextlib.suppress(pynvml.NVMLError):
        fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)

    return {
        "index": index,
        "name": name,
        "gpu_utilization": util.gpu,
        "memory_utilization": util.memory,
        "memory_used": mem.used,
        "memory_total": mem.total,
        "memory_free": mem.free,
        "temperature": temperature,
        "power_usage_watts": power_usage,
        "power_limit_watts": power_limit,
        "fan_speed_percent": fan_speed,
    }


@router.get("/gpu")
async def list_gpus() -> dict:
    """List all available GPUs with their current stats."""
    if not _NVML_AVAILABLE:
        return {"gpus": [], "count": 0, "available": False}

    try:
        count = pynvml.nvmlDeviceGetCount()
        gpus = [_get_gpu_info(i) for i in range(count)]
    except pynvml.NVMLError as e:
        raise HTTPException(status_code=503, detail=f"GPU monitoring unavailable: {e}") from e
    else:
        return {"gpus": gpus, "count": count, "available": True}


@router.get("/gpu/{gpu_index}")
async def get_gpu(gpu_index: int) -> dict:
    """Get stats for a specific GPU by index."""
    if not _NVML_AVAILABLE:
        raise HTTPException(status_code=503, detail="GPU monitoring unavailable: NVML not initialized")

    try:
        count = pynvml.nvmlDeviceGetCount()
        if gpu_index < 0 or gpu_index >= count:
            raise HTTPException(status_code=404, detail=f"GPU index {gpu_index} not found (count={count})")
        return _get_gpu_info(gpu_index)
    except pynvml.NVMLError as e:
        raise HTTPException(status_code=503, detail=f"GPU monitoring unavailable: {e}") from e
