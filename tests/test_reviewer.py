"""Tests for the reviewer module."""

import pytest
from sibyl.reviewer import ReviewCriteria, PaperReview, ReviewSystem
from sibyl.config import LLMConfig


def test_review_criteria_creation():
    """Test creating review criteria."""
    criteria = ReviewCriteria(
        novelty="High novelty",
        methodology="Strong methodology",
        results="Significant results",
        clarity="Clear writing",
        impact="High impact",
        limitations="Minor limitations",
        strengths="Multiple strengths",
        overall_score=8,
        recommendation="Accept",
        detailed_feedback="Well done",
    )

    assert criteria.novelty == "High novelty"
    assert criteria.overall_score == 8
    assert criteria.recommendation == "Accept"


def test_review_criteria_score_validation():
    """Test score validation in review criteria."""
    with pytest.raises(ValueError):
        ReviewCriteria(
            novelty="Test",
            methodology="Test",
            results="Test",
            clarity="Test",
            impact="Test",
            limitations="Test",
            strengths="Test",
            overall_score=11,  # Invalid: > 10
            recommendation="Accept",
            detailed_feedback="Test",
        )


def test_paper_review_creation():
    """Test creating a paper review."""
    criteria = ReviewCriteria(
        novelty="High",
        methodology="Strong",
        results="Good",
        clarity="Clear",
        impact="High",
        limitations="Minor",
        strengths="Many",
        overall_score=8,
        recommendation="Accept",
        detailed_feedback="Good work",
    )

    review = PaperReview(
        paper_title="Test Paper",
        reviewer_model="TestModel",
        criteria=criteria,
        raw_response="Test response",
    )

    assert review.paper_title == "Test Paper"
    assert review.reviewer_model == "TestModel"
    assert review.criteria.overall_score == 8
