"""Response models for GPU monitoring."""

from typing import Literal

from pydantic import BaseModel


class GpuProcess(BaseModel):
    """A process using a GPU."""

    pid: int
    name: str
    memory_bytes: int
    type: Literal["compute", "graphics"]


class GpuStats(BaseModel):
    """Current stats of one GPU."""

    index: int
    name: str
    gpu_utilization: float
    memory_utilization: float
    memory_used: int
    memory_total: int
    memory_free: int
    temperature: float | None
    power_usage_watts: float | None
    power_limit_watts: float | None
    fan_speed_percent: float | None
    processes: list[GpuProcess]


class GpuList(BaseModel):
    """All GPUs on this machine."""

    gpus: list[GpuStats]
    count: int
    available: bool
    vendor: Literal["nvidia", "apple"] | None
