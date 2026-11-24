"""Hold GPU resources only while a review runs.

Model servers (per-GPU Ollama, vLLM) and Marker's PDF models are started when a review needs them. Once no review has
run for ``SIBYL_GPU_IDLE_SECONDS`` (a grace period so back-to-back reviews do not reload everything), they are released
and the GPUs are left free until the next review.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from sibyl.inference.base import env_float

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

logger = logging.getLogger(__name__)

DEFAULT_IDLE_SECONDS = 60.0


class GpuActivity:
    """Count running reviews and call ``release`` once none has run for ``idle_seconds``."""

    def __init__(self, release: Callable[[], Awaitable[None]], idle_seconds: float | None = None) -> None:
        """Nothing is released until the first review has ended."""
        self.release = release
        self.idle_seconds = idle_seconds if idle_seconds is not None else env_float("SIBYL_GPU_IDLE_SECONDS", DEFAULT_IDLE_SECONDS)
        self.active = 0
        self._timer: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        """Held while releasing, so a review that starts meanwhile waits instead of using a server being stopped."""

    @contextlib.asynccontextmanager
    async def review(self) -> AsyncIterator[None]:
        """Mark a review as running for the duration of the block."""
        if self._timer is not None:  # a pending release is no longer due
            self._timer.cancel()
            self._timer = None
        async with self._lock:
            self.active += 1
        try:
            yield
        finally:
            self.active -= 1
            if self.active == 0:
                self._timer = asyncio.create_task(self._release_when_idle())

    async def _release_when_idle(self) -> None:
        await asyncio.sleep(self.idle_seconds)
        self._timer = None  # from here on the release runs to the end; a new review waits for it on the lock
        async with self._lock:
            if self.active:
                return
            logger.info("No review for %.0fs: releasing GPU resources", self.idle_seconds)
            try:
                await self.release()
            except Exception:
                logger.exception("Releasing GPU resources failed")

    async def aclose(self) -> None:
        """Cancel a pending release (the engine stops its servers on shutdown anyway)."""
        if self._timer is not None:
            self._timer.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._timer
            self._timer = None
