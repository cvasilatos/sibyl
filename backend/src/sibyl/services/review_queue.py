"""The review queue: reviews run in the background, one per GPU, in the order they were submitted.

A review no longer depends on the browser that submitted it: closing or reloading the page leaves it running, and
anyone opening the page sees the queue. Jobs are kept in ``<SIBYL_STORAGE_PATH>/review_jobs/`` (a JSON file and the
uploaded PDF each), so queued reviews survive a restart; reviews interrupted by a restart run again from the start.

Each GPU Sibyl schedules on runs one review at a time. A review that asked for a GPU waits for that one; the others
take the first free GPU. A job that cannot start does not hold up later jobs that can.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from pydantic import BaseModel

from sibyl.schemas.review_config import ReviewDetail, ReviewMode  # noqa: TC001 (pydantic needs them at runtime)
from sibyl.schemas.review_jobs import ACTIVE_STATUSES, ReviewJob
from sibyl.services.review_pipeline import ReviewFailedError, ReviewInputs, planned_steps, run_review

if TYPE_CHECKING:
    from pathlib import Path

    from sibyl.inference import InferenceEngine
    from sibyl.schemas.ws import ReviewProgress
    from sibyl.services.auth import User
    from sibyl.services.gpu_activity import GpuActivity
    from sibyl.storage.engine import Engine as Storage

logger = logging.getLogger(__name__)

FINISHED_RETENTION = timedelta(days=7)
"""Finished jobs the user has not dismissed are dropped after this long (the reviews stay in the library)."""
DEFAULT_MAX_QUEUED_PER_USER = 10


class QueueError(ValueError):
    """A request the queue refuses, with the HTTP status that describes why."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        """Keep the message and the HTTP status to answer with."""
        super().__init__(message)
        self.status_code = status_code


class _Settings(BaseModel):
    """What ``ReviewInputs`` needs besides the paper, as saved with the job."""

    vlm: str | None = None
    related: bool | None = None
    sources: tuple[str, ...] | None = None
    detail: ReviewDetail | None = None
    mode: ReviewMode | None = None
    review_form: str | None = None
    review_form_filename: str | None = None
    conference_id: str | None = None


class _StoredJob(BaseModel):
    """A job as saved on disk: what the API shows plus what only the pipeline needs."""

    job: ReviewJob
    settings: _Settings


def _now() -> str:
    return datetime.now(UTC).isoformat()


def max_queued_per_user() -> int:
    """How many reviews one user may have waiting or running at once (``SIBYL_MAX_QUEUED_PER_USER``)."""
    try:
        return max(int(os.getenv("SIBYL_MAX_QUEUED_PER_USER", str(DEFAULT_MAX_QUEUED_PER_USER))), 1)
    except ValueError:
        return DEFAULT_MAX_QUEUED_PER_USER


class ReviewQueue:
    """Runs submitted reviews in the background, at most one per GPU."""

    def __init__(self, engine: InferenceEngine, storage: Storage, gpu_activity: GpuActivity, directory: Path, gpus: list[int]) -> None:
        """Schedule on ``gpus`` (review slot n + 1 for GPU n); with none, run one review at a time on slot 0 (engine's choice)."""
        self.engine = engine
        self.storage = storage
        self.gpu_activity = gpu_activity
        self.directory = directory
        self.gpus = sorted(gpus)
        self._hosts = [gpu + 1 for gpu in self.gpus] or [0]
        self._jobs: dict[str, _StoredJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._busy: dict[int, str] = {}
        """Review slot -> id of the job running on it."""
        self._closing = False

    @property
    def slots(self) -> int:
        """How many reviews run at once."""
        return len(self._hosts)

    # --- Persistence ------------------------------------------------------------------------------------------------

    def _json_path(self, job_id: str) -> Path:
        return self.directory / f"{job_id}.json"

    def pdf_path(self, job_id: str) -> Path:
        """Where a job's uploaded paper is kept until the review is saved."""
        return self.directory / f"{job_id}.pdf"

    def _save(self, stored: _StoredJob) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._json_path(stored.job.id)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(stored.model_dump_json(), encoding="utf-8")
        temporary.replace(path)

    def _forget(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)
        for path in (self._json_path(job_id), self.pdf_path(job_id)):
            path.unlink(missing_ok=True)

    def load(self) -> None:
        """Read saved jobs: queued ones wait again, ones a restart interrupted run again, old finished ones are dropped."""
        if not self.directory.is_dir():
            return
        cutoff = datetime.now(UTC) - FINISHED_RETENTION
        for path in sorted(self.directory.glob("*.json")):
            try:
                stored = _StoredJob.model_validate_json(path.read_text(encoding="utf-8"))
            except ValueError:
                logger.warning("Ignoring unreadable review job %s", path.name)
                continue
            job = stored.job
            if job.status in ACTIVE_STATUSES and not self.pdf_path(job.id).is_file():
                job.status, job.message, job.finished_at = "failed", "The uploaded paper was lost while the server was down", _now()
            elif job.status == "running":
                job.status, job.step, job.progress, job.gpu, job.started_at = "queued", None, 0, None, None
                job.message = "Interrupted by a server restart; queued to run again"
            elif job.status not in ACTIVE_STATUSES and datetime.fromisoformat(job.finished_at or job.created_at) < cutoff:
                self._forget(job.id)
                continue
            self._jobs[job.id] = stored
            self._save(stored)
        self._jobs = dict(sorted(self._jobs.items(), key=lambda item: item[1].job.created_at))
        if self._jobs:
            logger.info("Loaded %d review job(s), %d waiting", len(self._jobs), sum(s.job.status == "queued" for s in self._jobs.values()))

    # --- Queries ----------------------------------------------------------------------------------------------------

    def _with_position(self, job: ReviewJob) -> ReviewJob:
        if job.status != "queued":
            return job.model_copy(update={"position": None})
        queued = [s.job.id for s in self._jobs.values() if s.job.status == "queued"]
        return job.model_copy(update={"position": queued.index(job.id) + 1})

    def get(self, job_id: str) -> ReviewJob | None:
        """Return a job by id."""
        stored = self._jobs.get(job_id)
        return self._with_position(stored.job) if stored else None

    def visible_to(self, user: User) -> list[ReviewJob]:
        """Everyone's queued and running jobs, and ``user``'s finished ones, oldest first."""
        return [self._with_position(s.job) for s in self._jobs.values() if s.job.status in ACTIVE_STATUSES or s.job.owner == user.username]

    # --- Changes ----------------------------------------------------------------------------------------------------

    def submit(self, inputs: ReviewInputs, *, job_id: str, requested_gpu: int | None, form_name: str | None) -> ReviewJob:
        """Queue a review of the paper already saved at ``pdf_path(job_id)``; it starts as soon as a GPU is free."""
        if self._closing:
            raise QueueError("The server is shutting down", status_code=503)
        if requested_gpu is not None and self.gpus and requested_gpu not in self.gpus:
            raise QueueError(f"GPU {requested_gpu} is not available (GPUs: {', '.join(str(g) for g in self.gpus)})")
        if not self.gpus:
            requested_gpu = None  # nothing to choose from: the engine places the review
        waiting = sum(s.job.owner == inputs.owner and s.job.status in ACTIVE_STATUSES for s in self._jobs.values())
        if waiting >= max_queued_per_user():
            raise QueueError(f"You already have {waiting} reviews waiting or running; wait for one to finish", status_code=429)
        job = ReviewJob(
            id=job_id,
            owner=inputs.owner,
            filename=inputs.filename,
            model=inputs.model,
            form_name=form_name,
            status="queued",
            requested_gpu=requested_gpu,
            steps=planned_steps(self.engine.name, inputs),
            message="Waiting for a free GPU" if requested_gpu is None else f"Waiting for GPU {requested_gpu}",
            created_at=_now(),
        )
        stored = _StoredJob(
            job=job,
            settings=_Settings(
                vlm=inputs.vlm,
                related=inputs.related,
                sources=inputs.sources,
                detail=inputs.detail,
                mode=inputs.mode,
                review_form=inputs.review_form,
                review_form_filename=inputs.review_form_filename,
                conference_id=inputs.conference_id,
            ),
        )
        self._jobs[job.id] = stored
        self._save(stored)
        logger.info("Queued review %s of %s for %s", job.id, job.filename, job.owner)
        self.dispatch()
        return self.get(job.id) or job

    def cancel(self, job_id: str, user: User) -> ReviewJob:
        """Cancel a queued or running job, or dismiss a finished one from the list."""
        stored = self._jobs.get(job_id)
        if stored is None:
            raise QueueError("Review not found", status_code=404)
        job = stored.job
        if not user.can_manage(job.owner):
            raise QueueError("Only the person who submitted this review (or an admin) can cancel it", status_code=403)
        if job.status == "queued":
            job.status, job.message, job.finished_at = "cancelled", f"Cancelled by {user.username}", _now()
            self.pdf_path(job_id).unlink(missing_ok=True)
            self._save(stored)
            logger.info("Cancelled queued review %s", job_id)
        elif job.status == "running":
            job.message = "Cancelling (the current step finishes first)..."
            task = self._tasks.get(job_id)
            if task is not None:
                task.cancel(f"Cancelled by {user.username}")
            logger.info("Cancelling running review %s", job_id)
        else:
            self._forget(job_id)
            return job
        return self._with_position(job)

    def dispatch(self) -> None:
        """Start every queued job that has a free GPU, oldest first."""
        if self._closing:
            return
        for stored in list(self._jobs.values()):
            job = stored.job
            if job.status != "queued":
                continue
            free = [host for host in self._hosts if host not in self._busy]
            if job.requested_gpu is not None:
                free = [host for host in free if host == job.requested_gpu + 1]
            if not free:
                continue
            host = free[0]
            self._busy[host] = job.id
            job.status, job.started_at, job.gpu = "running", _now(), host - 1 if host > 0 else None
            job.message = "Starting..."
            self._save(stored)
            self._tasks[job.id] = asyncio.create_task(self._run(stored, host), name=f"review-{job.id}")

    async def _run(self, stored: _StoredJob, host: int) -> None:
        job, settings = stored.job, stored.settings
        inputs = ReviewInputs(pdf_path=self.pdf_path(job.id), filename=job.filename, model=job.model, owner=job.owner, **settings.model_dump())

        async def send(message: ReviewProgress) -> None:
            if job.status == "running" and not job.message.startswith("Cancelling"):
                job.step, job.progress, job.message = message.step, message.progress, message.message
            else:
                job.step, job.progress = message.step, message.progress

        logger.info("Starting review %s of %s for %s on slot %s", job.id, job.filename, job.owner, host)
        interrupted = False
        try:
            async with self.gpu_activity.review():
                review_id, results = await run_review(self.engine, self.storage, inputs, host=host, send=send)
        except asyncio.CancelledError:
            if self._closing:  # shutting down: leave it "running" on disk so the next start runs it again
                interrupted = True
                raise
            job.status, job.message = "cancelled", "Cancelled"
        except ReviewFailedError as e:
            job.status, job.message = "failed", str(e)
        except Exception as e:
            logger.exception("Review %s failed", job.id)
            job.status, job.message = "failed", str(e) or type(e).__name__
        else:
            job.status, job.step, job.progress, job.message = "completed", None, 100, "Review complete!"
            job.review_id, job.results = review_id, results
        finally:
            self._busy.pop(host, None)
            self._tasks.pop(job.id, None)
            if not interrupted:
                job.finished_at = _now()
                self.pdf_path(job.id).unlink(missing_ok=True)  # saved with the review, or no longer needed
                self._save(stored)
                logger.info("Review %s %s", job.id, job.status)
                self.dispatch()

    async def aclose(self) -> None:
        """Stop running reviews without marking them finished, so the next start runs them again."""
        self._closing = True
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel("Server shutting down")
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task


def new_job_id() -> str:
    """Return a fresh job id."""
    return uuid.uuid4().hex
