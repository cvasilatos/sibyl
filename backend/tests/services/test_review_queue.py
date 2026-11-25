"""The review queue: one review per GPU, in order, independent of any browser, surviving restarts."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from sibyl.schemas.ws import ReviewProgress, ReviewResults
from sibyl.services import review_queue
from sibyl.services.auth import User
from sibyl.services.gpu_activity import GpuActivity
from sibyl.services.review_pipeline import ReviewFailedError, ReviewInputs
from sibyl.services.review_queue import QueueError, ReviewQueue

ALICE = User("alice", is_admin=False)
BOB = User("bob", is_admin=False)
ADMIN = User("root", is_admin=True)


class FakeEngine:
    name = "ollama"


class FakeRuns:
    """Stands in for ``run_review``: each run waits until the test finishes it, and records its slot."""

    def __init__(self) -> None:
        self.hosts: dict[str, int] = {}
        self.release: dict[str, asyncio.Event] = {}
        self.fail: dict[str, Exception] = {}

    async def __call__(self, _engine, _storage, inputs: ReviewInputs, *, host: int, send) -> tuple[str, ReviewResults]:
        job_id = inputs.pdf_path.stem
        self.hosts[job_id] = host
        await send(ReviewProgress(step="parse", progress=10, message="Parsing"))
        await self.release.setdefault(job_id, asyncio.Event()).wait()
        if job_id in self.fail:
            raise self.fail[job_id]
        return f"review_{job_id}", ReviewResults(paper_title="P", reviews=[])

    def finish(self, job_id: str) -> None:
        self.release.setdefault(job_id, asyncio.Event()).set()


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch) -> FakeRuns:
    fake = FakeRuns()
    monkeypatch.setattr(review_queue, "run_review", fake)
    return fake


def make_queue(directory: Path, gpus: list[int]) -> ReviewQueue:
    return ReviewQueue(FakeEngine(), AsyncMock(), GpuActivity(AsyncMock(), idle_seconds=60), directory, gpus)  # ty: ignore[invalid-argument-type]


def submit(queue: ReviewQueue, owner: User = ALICE, gpu: int | None = None) -> str:
    job_id = review_queue.new_job_id()
    queue.directory.mkdir(parents=True, exist_ok=True)
    queue.pdf_path(job_id).write_bytes(b"%PDF")
    inputs = ReviewInputs(pdf_path=queue.pdf_path(job_id), filename="p.pdf", model="m", owner=owner.username, vlm="none", related=False)
    return queue.submit(inputs, job_id=job_id, requested_gpu=gpu, form_name=None).id


def status(queue: ReviewQueue, job_id: str) -> str:
    job = queue.get(job_id)
    assert job is not None
    return job.status


async def settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


def test_one_review_per_gpu_in_order(tmp_path: Path, runs: FakeRuns) -> None:
    async def scenario() -> None:
        queue = make_queue(tmp_path, gpus=[0, 1])
        first, second, third = submit(queue), submit(queue), submit(queue)
        await settle()
        assert [status(queue, j) for j in (first, second, third)] == ["running", "running", "queued"]
        assert (runs.hosts[first], runs.hosts[second]) == (1, 2)
        third_job = queue.get(third)
        assert third_job is not None
        assert third_job.position == 1
        running = queue.get(first)
        assert running is not None
        assert (running.gpu, running.step, running.progress) == (0, "parse", 10)

        runs.finish(second)
        await settle()
        assert status(queue, second) == "completed"
        assert status(queue, third) == "running"
        assert runs.hosts[third] == 2  # took the GPU that freed up
        done = queue.get(second)
        assert done is not None
        assert (done.review_id, done.progress, done.finished_at is not None) == (f"review_{second}", 100, True)
        assert not queue.pdf_path(second).exists()
        for job_id in (first, third):
            runs.finish(job_id)
        await settle()

    asyncio.run(scenario())


def test_pinned_review_waits_without_blocking_others(tmp_path: Path, runs: FakeRuns) -> None:
    async def scenario() -> None:
        queue = make_queue(tmp_path, gpus=[0, 1])
        on_zero = submit(queue, gpu=0)
        also_zero = submit(queue, gpu=0)
        anywhere = submit(queue)
        await settle()
        assert [status(queue, j) for j in (on_zero, also_zero, anywhere)] == ["running", "queued", "running"]
        assert runs.hosts[anywhere] == 2
        waiting = queue.get(also_zero)
        assert waiting is not None
        assert waiting.message == "Waiting for GPU 0"

        runs.finish(on_zero)
        await settle()
        assert status(queue, also_zero) == "running"
        assert runs.hosts[also_zero] == 1
        for job_id in (also_zero, anywhere):
            runs.finish(job_id)
        await settle()

    asyncio.run(scenario())


def test_without_gpus_one_review_runs_at_a_time(tmp_path: Path, runs: FakeRuns) -> None:
    async def scenario() -> None:
        queue = make_queue(tmp_path, gpus=[])
        first, second = submit(queue, gpu=3), submit(queue)
        await settle()
        assert queue.slots == 1
        assert [status(queue, j) for j in (first, second)] == ["running", "queued"]
        assert runs.hosts[first] == 0  # the engine places it
        runs.finish(first)
        await settle()
        assert status(queue, second) == "running"
        runs.finish(second)
        await settle()

    asyncio.run(scenario())


def test_failed_and_cancelled_reviews_free_the_gpu(tmp_path: Path, runs: FakeRuns) -> None:
    async def scenario() -> None:
        queue = make_queue(tmp_path, gpus=[0])
        failing, cancelled, last = submit(queue), submit(queue), submit(queue)
        runs.fail[failing] = ReviewFailedError("Error reviewing with m: boom")
        await settle()
        runs.finish(failing)
        await settle()
        failed = queue.get(failing)
        assert failed is not None
        assert (failed.status, failed.message) == ("failed", "Error reviewing with m: boom")
        assert not queue.pdf_path(failing).exists()

        assert status(queue, cancelled) == "running"
        assert queue.cancel(cancelled, ALICE).message.startswith("Cancelling")
        await settle()
        assert status(queue, cancelled) == "cancelled"
        assert status(queue, last) == "running"
        runs.finish(last)
        await settle()

    asyncio.run(scenario())


def test_only_owner_or_admin_may_cancel(tmp_path: Path, runs: FakeRuns) -> None:
    async def scenario() -> None:
        queue = make_queue(tmp_path, gpus=[0])
        running, queued = submit(queue), submit(queue)
        await settle()
        with pytest.raises(QueueError) as error:
            queue.cancel(queued, BOB)
        assert error.value.status_code == 403
        assert queue.cancel(queued, ADMIN).status == "cancelled"
        with pytest.raises(QueueError) as missing:
            queue.cancel("nope", ALICE)
        assert missing.value.status_code == 404
        queue.cancel(running, ALICE)
        await settle()

    asyncio.run(scenario())


def test_everyone_sees_the_queue_but_only_their_finished_reviews(tmp_path: Path, runs: FakeRuns) -> None:
    async def scenario() -> None:
        queue = make_queue(tmp_path, gpus=[0])
        alices, bobs = submit(queue, ALICE), submit(queue, BOB)
        await settle()
        assert [j.id for j in queue.visible_to(BOB)] == [alices, bobs]
        runs.finish(alices)
        await settle()
        assert [j.id for j in queue.visible_to(BOB)] == [bobs]
        assert [j.id for j in queue.visible_to(ALICE)] == [alices, bobs]
        runs.finish(bobs)
        await settle()

    asyncio.run(scenario())


def test_reviews_survive_a_restart(tmp_path: Path, runs: FakeRuns) -> None:
    async def before_restart() -> tuple[str, str, str]:
        queue = make_queue(tmp_path, gpus=[0])
        done, interrupted, waiting = submit(queue), submit(queue), submit(queue)
        await settle()
        runs.finish(done)
        await settle()
        assert status(queue, interrupted) == "running"
        await queue.aclose()
        return done, interrupted, waiting

    done, interrupted, waiting = asyncio.run(before_restart())
    stale = json.loads((tmp_path / f"{done}.json").read_text())
    old = json.loads(json.dumps(stale))
    old["job"]["id"] = "0" * 32
    old["job"]["finished_at"] = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    (tmp_path / f"{'0' * 32}.json").write_text(json.dumps(old))

    async def after_restart() -> None:
        runs.release.clear()  # events of the first run belong to its event loop
        queue = make_queue(tmp_path, gpus=[0])
        queue.load()
        assert queue.get("0" * 32) is None  # finished long ago: dropped
        assert not (tmp_path / f"{'0' * 32}.json").exists()
        assert status(queue, done) == "completed"
        again = queue.get(interrupted)
        assert again is not None
        assert (again.status, again.position, again.message) == ("queued", 1, "Interrupted by a server restart; queued to run again")
        queue.dispatch()
        await settle()
        assert status(queue, interrupted) == "running"  # runs again first, ahead of the job submitted after it
        assert status(queue, waiting) == "queued"
        for job_id in (interrupted, waiting):
            runs.finish(job_id)
            await settle()
        assert status(queue, waiting) == "completed"

    asyncio.run(after_restart())


def test_queued_review_whose_paper_vanished_fails_on_load(tmp_path: Path, runs: FakeRuns) -> None:
    async def before() -> str:
        queue = make_queue(tmp_path, gpus=[0])
        queue.dispatch = lambda: None  # ty: ignore[invalid-assignment]
        return submit(queue)

    job_id = asyncio.run(before())
    (tmp_path / f"{job_id}.pdf").unlink()
    queue = make_queue(tmp_path, gpus=[0])
    queue.load()
    assert status(queue, job_id) == "failed"
