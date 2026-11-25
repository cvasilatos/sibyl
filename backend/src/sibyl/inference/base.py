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


CHARS_PER_TOKEN = 3.0
"""Conservative estimate for English scientific text with Markdown/LaTeX (real ratio is ~3.5-4)."""


def estimate_tokens(text: str) -> int:
    """Rough token count used for context budgeting; errs high."""
    return int(len(text) / CHARS_PER_TOKEN) + 1


DEFAULT_CONTEXT = 32768
"""Context window when ``SIBYL_MAX_CONTEXT`` is unset, or when it is ``model`` but the model's limit is unknown."""


def max_context_setting() -> int | None:
    """Read ``SIBYL_MAX_CONTEXT``: a token cap (default 32768), or ``None`` for ``model`` (each model's full limit)."""
    value = os.getenv("SIBYL_MAX_CONTEXT", "").strip()
    if value.lower() == "model":
        return None
    return int(value) if value else DEFAULT_CONTEXT


def cap_context(native: int | None, setting: int | None) -> int:
    """Pick the context window from the model's own limit (``None`` if unknown) and the ``SIBYL_MAX_CONTEXT`` setting."""
    if setting is None:
        return native or DEFAULT_CONTEXT
    return min(setting, native) if native else setting


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
    context_length: int
    """Context window (prompt + output tokens)."""
    max_tokens: int | None = None
    """Output cap; ``None`` lets the model write until the context window is full."""
    slot: int = AUTO_SLOT
    on_status: Callable[[str], Awaitable[None]] | None = field(default=None, repr=False)
    images: list[str] = field(default_factory=list, repr=False)
    """Base64-encoded JPEG images sent with the prompt (vision-language models only)."""
    keep_loaded: bool = False
    """Hint that more requests for the same model follow, so the engine should not unload it yet."""


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
        """Context window (prompt + output tokens) to use for ``model``; this engine cannot ask for the model's limit."""
        return cap_context(None, max_context_setting())

    async def context_window(self, model: str) -> int:
        """Context window for ``model``; engines that must ask their server for the model's limit override this."""
        return self.context_length(model)

    def info(self) -> dict[str, Any]:
        """Describe this engine for the frontend."""
        return {"name": self.name, "label": self.label, "supports_downloads": self.supports_downloads}

    def review_gpus(self) -> list[int]:
        """GPUs the review queue runs one review on each (review slot n + 1 for GPU n).

        Empty when the engine cannot pin a review to a GPU: the queue then runs one review at a time and lets the
        engine place it.
        """
        return []

    async def release_gpus(self) -> None:  # noqa: B027
        """Free the GPU memory this engine holds (model servers, loaded models) while no review runs; reviews start them again."""

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
