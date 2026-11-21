"""Response models for the inference engine and its models."""

from pydantic import BaseModel


class VllmServer(BaseModel):
    """A running vLLM server."""

    gpu: int
    model: str
    port: int
    inflight: int
    alive: bool


class EngineInfo(BaseModel):
    """The active inference engine and the machine it runs on. ``gpus`` and ``servers`` are set by vLLM only."""

    name: str
    label: str
    supports_downloads: bool
    platform: str
    machine: str
    gpus: list[int] | None = None
    servers: list[VllmServer] | None = None


class InstalledModel(BaseModel):
    """A model downloaded into the engine."""

    model: str
    size: int
    modified_at: str
    digest: str


class InstalledModels(BaseModel):
    """Models downloaded into the engine."""

    models: list[InstalledModel]
    count: int


class AvailableModel(BaseModel):
    """A model the engine can download."""

    name: str
    description: str
    size: str
    installed: bool
    installed_variants: list[str] = []


class AvailableModels(BaseModel):
    """Models the engine can download."""

    models: list[AvailableModel]
    count: int


class ModelTags(BaseModel):
    """Downloadable size variants of a catalog model."""

    model: str
    tags: list[str]


class DeletedModel(BaseModel):
    """Result of deleting a model."""

    message: str
    model: str
