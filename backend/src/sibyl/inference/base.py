"""Engine-agnostic interface for running local open-source LLMs."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

AUTO_SLOT = 0
"""Slot value meaning "let the engine pick a GPU/host". Slot ``n >= 1`` targets GPU ``n - 1``."""


class EngineOperationNotSupportedError(RuntimeError):
    """Raised when an engine cannot perform an operation (e.g. downloads on an external server)."""


@dataclass(slots=True)
class GenerationRequest:
    """A single structured (JSON-schema constrained) generation request."""

    model: str
    system: str
    prompt: str
    schema: dict[str, Any]
    temperature: float
    max_tokens: int
    context_length: int
    slot: int = AUTO_SLOT
    on_status: Callable[[str], Awaitable[None]] | None = field(default=None, repr=False)


class InferenceEngine(ABC):
    """A backend that can manage and run open-source models."""

    name: str = "engine"
    label: str = "Engine"
    supports_downloads: bool = True
    """Whether Sibyl can download/delete models through this engine."""

    @abstractmethod
    async def list_installed(self) -> list[dict[str, Any]]:
        """Return installed models as ``{model, size, modified_at, digest}`` dicts."""

    @abstractmethod
    async def list_catalog(self) -> list[dict[str, Any]]:
        """Return downloadable models as ``{name, description, size, installed, installed_variants}`` dicts."""

    @abstractmethod
    async def list_variants(self, name: str) -> list[str]:
        """Return downloadable variants (size tags) of a catalog entry; empty when not applicable."""

    @abstractmethod
    def pull(self, model: str) -> AsyncIterator[dict[str, Any]]:
        """Download a model, yielding ``{status, completed?, total?}`` progress dicts and finally ``{status: "success"}``."""

    @abstractmethod
    async def delete(self, model: str) -> None:
        """Delete a downloaded model."""

    @abstractmethod
    async def generate_json(self, request: GenerationRequest) -> str:
        """Run a schema-constrained generation and return the raw JSON text."""

    def context_length(self, model: str) -> int:  # noqa: ARG002
        """Context window (prompt + output tokens) to use for ``model``."""
        return env_int("SIBYL_MAX_CONTEXT", 32768)

    def info(self) -> dict[str, Any]:
        """Describe this engine for the frontend."""
        return {"name": self.name, "label": self.label, "supports_downloads": self.supports_downloads}

    async def aclose(self) -> None:  # noqa: B027
        """Release engine resources (processes, connections)."""


def env_int(name: str, default: int) -> int:
    """Read an integer environment variable with a default."""
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


def env_float(name: str, default: float) -> float:
    """Read a float environment variable with a default."""
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default
