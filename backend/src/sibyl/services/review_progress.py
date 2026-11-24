"""Overall progress of a review run, built from the steps it takes and the work done inside each.

Each step owns a share of the bar, weighted by how long it usually takes; skipped steps give their share to the
others. Steps that can count their work (figures described, arXiv searches, review sections) report ``(done, total)``
and the bar moves within the step's share; the next status message carries the new percentage.
"""

from collections.abc import Awaitable, Callable

from sibyl.schemas.ws import ReviewProgress, ReviewStep

STEP_WEIGHTS: dict[ReviewStep, int] = {"parse": 20, "figures": 15, "related_work": 10, "review": 50, "save": 5}
"""Relative share of the bar for each step (rough share of a typical run's time)."""


class ReviewProgressTracker:
    """Turns per-step progress into the overall percentage sent to the client."""

    def __init__(self, steps: list[ReviewStep], send: Callable[[ReviewProgress], Awaitable[None]]) -> None:
        """Lay out ``steps`` (in order) along the bar; ``send`` delivers each progress message."""
        total = sum(STEP_WEIGHTS[step] for step in steps) or 1
        self._spans: dict[ReviewStep, tuple[float, float]] = {}
        start = 0.0
        for step in steps:
            width = 100 * STEP_WEIGHTS[step] / total
            self._spans[step] = (start, width)
            start += width
        self._done: dict[ReviewStep, float] = {}
        self._percent = 0
        self._send = send

    def percent(self, step: ReviewStep) -> int:
        """Overall percentage for the work done so far in ``step``; never goes back, and 100 is left for completion."""
        start, width = self._spans.get(step, (self._percent, 0.0))
        self._percent = min(max(self._percent, int(start + width * self._done.get(step, 0.0))), 99)
        return self._percent

    async def report(self, step: ReviewStep, message: str, *, done: float | None = None) -> None:
        """Send ``message`` for ``step``; ``done`` (0-1) first records how much of the step is finished."""
        if done is not None:
            self.advance(step, done)
        await self._send(ReviewProgress(step=step, progress=self.percent(step), message=message))

    def advance(self, step: ReviewStep, done: float) -> None:
        """Record that ``done`` (0-1) of ``step`` is finished; it shows with the step's next message."""
        self._done[step] = max(self._done.get(step, 0.0), min(max(done, 0.0), 1.0))

    def on_status(self, step: ReviewStep) -> Callable[[str], Awaitable[None]]:
        """Return a status callback for a service working on ``step``."""

        async def status(message: str) -> None:
            await self.report(step, message)

        return status

    def on_progress(self, step: ReviewStep) -> Callable[[int, int], Awaitable[None]]:
        """Return a ``(done, total)`` callback for a service that can count its work on ``step``."""

        async def progress(done: int, total: int) -> None:
            self.advance(step, done / total if total else 0.0)

        return progress
