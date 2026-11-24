"""Pytest configuration and fixtures."""

import os
import shutil
import tempfile

import pytest

# Point storage at a throwaway directory before any test imports sibyl: config.STORAGE_PATH and state.storage are
# fixed at import, and tests that drive the app (e.g. DELETE /api/reviews) would otherwise wipe the real library.
_TEST_STORAGE = tempfile.mkdtemp(prefix="sibyl-test-storage-")
os.environ["SIBYL_STORAGE_PATH"] = _TEST_STORAGE


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
