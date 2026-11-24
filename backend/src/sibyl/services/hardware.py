"""Hardware discovery that works on NVIDIA/Linux and Apple Silicon/macOS."""

from __future__ import annotations

import contextlib
import functools
import logging
import platform
import re
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

IS_MACOS = platform.system() == "Darwin"

try:
    import pynvml

    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except Exception:
    NVML_AVAILABLE = False


def torch_device(slot: int) -> str:
    """Return the torch device for a review slot (``0`` = auto, ``n`` = GPU ``n - 1``)."""
    import torch  # noqa: PLC0415

    if torch.cuda.is_available():
        index = slot - 1 if slot > 0 else least_busy_gpu()
        return f"cuda:{index if index < torch.cuda.device_count() else 0}"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def least_busy_gpu() -> int:
    """Index of the NVIDIA GPU with the lowest utilization (then most free memory); 0 if unknown."""
    with contextlib.suppress(Exception):
        gpus = list_gpus()["gpus"] if NVML_AVAILABLE else []
        if gpus:
            return int(min(gpus, key=lambda g: (g["gpu_utilization"], -g["memory_free"]))["index"])
    return 0


def nvidia_gpu_count() -> int:
    """Return the number of NVIDIA GPUs visible through NVML."""
    if not NVML_AVAILABLE:
        return 0
    try:
        return int(pynvml.nvmlDeviceGetCount())
    except pynvml.NVMLError:
        return 0


def list_gpus() -> dict[str, Any]:
    """Return GPU stats for whatever accelerator this machine has."""
    if NVML_AVAILABLE:
        count = nvidia_gpu_count()
        return {"gpus": [nvidia_gpu_info(i) for i in range(count)], "count": count, "available": True, "vendor": "nvidia"}
    if IS_MACOS:
        gpu = apple_gpu_info()
        if gpu is not None:
            return {"gpus": [gpu], "count": 1, "available": True, "vendor": "apple"}
    return {"gpus": [], "count": 0, "available": False, "vendor": None}


def nvidia_gpu_info(index: int) -> dict[str, Any]:
    """Return stats for a single NVIDIA GPU by index."""
    handle = pynvml.nvmlDeviceGetHandleByIndex(index)
    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
    mem = pynvml.nvmlDeviceGetMemoryInfo(handle)

    temperature: int | None = None
    with contextlib.suppress(pynvml.NVMLError):
        temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

    power_usage: float | None = None
    power_limit: float | None = None
    with contextlib.suppress(pynvml.NVMLError):
        power_usage = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
        power_limit = pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000.0

    fan_speed: int | None = None
    with contextlib.suppress(pynvml.NVMLError):
        fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)

    processes: list[dict[str, Any]] = []
    for proc_type, getter in (("compute", pynvml.nvmlDeviceGetComputeRunningProcesses), ("graphics", pynvml.nvmlDeviceGetGraphicsRunningProcesses)):
        with contextlib.suppress(pynvml.NVMLError):
            for proc in getter(handle):
                info: dict[str, Any] = {"pid": proc.pid, "memory_bytes": proc.usedGpuMemory or 0, "type": proc_type, "name": ""}
                with contextlib.suppress(Exception):
                    info["name"] = pynvml.nvmlSystemGetProcessName(proc.pid)
                processes.append(info)

    return {
        "index": index,
        "name": pynvml.nvmlDeviceGetName(handle),
        "gpu_utilization": util.gpu,
        "memory_utilization": util.memory,
        "memory_used": mem.used,
        "memory_total": mem.total,
        "memory_free": mem.free,
        "temperature": temperature,
        "power_usage_watts": power_usage,
        "power_limit_watts": power_limit,
        "fan_speed_percent": fan_speed,
        "processes": processes,
    }


def _run(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, timeout=5, check=False).stdout  # noqa: S603


@functools.cache
def _apple_static() -> tuple[str, int]:
    chip = _run("/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string").strip() or "Apple GPU"
    memsize = _run("/usr/sbin/sysctl", "-n", "hw.memsize").strip()
    return chip, int(memsize) if memsize.isdigit() else 0


_PERF_STAT = re.compile(r'"(Device Utilization %|In use system memory)"=(\d+)')


def parse_ioreg_performance(output: str) -> dict[str, int]:
    """Extract GPU utilization and memory from ``ioreg -c IOAccelerator`` output."""
    return {key: int(value) for key, value in _PERF_STAT.findall(output)}


def apple_gpu_info() -> dict[str, Any] | None:
    """Return Apple Silicon GPU stats (unified memory) without requiring sudo."""
    try:
        chip, memory_total = _apple_static()
        stats = parse_ioreg_performance(_run("/usr/sbin/ioreg", "-r", "-d", "1", "-w", "0", "-c", "IOAccelerator"))
    except (OSError, subprocess.SubprocessError):
        logger.debug("Apple GPU stats unavailable", exc_info=True)
        return None

    memory_used = stats.get("In use system memory", 0)
    return {
        "index": 0,
        "name": f"{chip} (unified memory)",
        "gpu_utilization": stats.get("Device Utilization %", 0),
        "memory_utilization": round(memory_used / memory_total * 100) if memory_total else 0,
        "memory_used": memory_used,
        "memory_total": memory_total,
        "memory_free": max(memory_total - memory_used, 0),
        "temperature": None,
        "power_usage_watts": None,
        "power_limit_watts": None,
        "fan_speed_percent": None,
        "processes": [],
    }
