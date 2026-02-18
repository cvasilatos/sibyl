"""Pytest configuration and fixtures."""

import pytest


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
