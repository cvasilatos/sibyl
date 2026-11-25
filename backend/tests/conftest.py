"""Pytest configuration and fixtures."""

import os
import shutil
import tempfile

import pytest

# Point storage at a throwaway directory before any test imports sibyl: config.STORAGE_PATH and state.storage are
# fixed at import, and tests that drive the app (e.g. DELETE /api/reviews) would otherwise wipe the real library.
_TEST_STORAGE = tempfile.mkdtemp(prefix="sibyl-test-storage-")
os.environ["SIBYL_STORAGE_PATH"] = _TEST_STORAGE
# A developer's backend/.env (loaded by sibyl.config, which never overrides set variables) must not turn sign-in on
# for the tests; the tests that need sign-in turn it on themselves.
os.environ["SIBYL_AUTH"] = "none"
for _name in ("SIBYL_AUTH_GROUP", "SIBYL_ADMIN_USERS", "SIBYL_SECRET_KEY", "SIBYL_CORS_ORIGINS", "SIBYL_MAX_QUEUED_PER_USER"):
    os.environ[_name] = ""  # set (not removed), so the .env value is not loaded either


def pytest_sessionfinish(session, exitstatus):
    """Remove the throwaway storage directory."""
    shutil.rmtree(_TEST_STORAGE, ignore_errors=True)


@pytest.fixture
def sample_paper_text():
    """Provide sample paper text for testing."""
    return """
    Title: A Novel Approach to Machine Learning

    Abstract:
    This paper presents a novel approach to machine learning that combines
    traditional techniques with modern deep learning methods.

    Introduction:
    Machine learning has become increasingly important in recent years...

    Methods:
    We developed a new algorithm that...

    Results:
    Our experiments show that...

    Conclusion:
    We have demonstrated that our approach...
    """


@pytest.fixture
def held_queue(tmp_path):
    """Install a review queue on the app that accepts jobs but never starts them, and return it.

    TestClient(app) does not run the lifespan, which creates the real queue.
    """
    from unittest.mock import AsyncMock

    from sibyl.inference.ollama_engine import OllamaEngine
    from sibyl.main import app
    from sibyl.services.gpu_activity import GpuActivity
    from sibyl.services.review_queue import ReviewQueue

    engine = getattr(app.state, "engine", None) or OllamaEngine(hosts=["http://ollama.test:11434"])
    queue = ReviewQueue(engine, AsyncMock(), GpuActivity(AsyncMock()), tmp_path / "review_jobs", gpus=[0, 1])
    queue.dispatch = lambda: None  # ty: ignore[invalid-assignment]  # keep jobs queued
    app.state.review_queue = queue
    return queue
