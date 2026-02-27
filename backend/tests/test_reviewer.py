"""Tests for the reviewer module."""

import pytest

from sibyl.reviewer import PaperReview, ReviewCriteria
from sibyl.web.model.llm_reply import LLMReply, Recommendation


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
        score=4,
        recommendation="Accept",
        detailed_feedback="Well done",
    )

    assert criteria.novelty == "High novelty"
    assert criteria.score == 4
    assert criteria.recommendation == "Accept"


def test_review_criteria_score_validation():
    """Test score validation in review criteria - score above MAX_SCORE raises ValueError."""
    with pytest.raises(ValueError):
        ReviewCriteria(
            novelty="Test",
            methodology="Test",
            results="Test",
            clarity="Test",
            impact="Test",
            limitations="Test",
            strengths="Test",
            score=6,  # Invalid: > MAX_SCORE (5)
            recommendation="Accept",
            detailed_feedback="Test",
        )


def test_review_criteria_score_minimum():
    """Test score validation - score below 1 raises ValueError."""
    with pytest.raises(ValueError):
        ReviewCriteria(
            novelty="Test",
            methodology="Test",
            results="Test",
            clarity="Test",
            impact="Test",
            limitations="Test",
            strengths="Test",
            score=0,  # Invalid: < 1
            recommendation="Accept",
            detailed_feedback="Test",
        )


def test_paper_review_creation():
    """Test creating a paper review."""
    criteria = LLMReply(
        novelty="High",
        methodology="Strong",
        results="Good",
        clarity="Clear",
        impact="High",
        limitations="Minor",
        strengths="Many",
        score=4,
        recommendation=Recommendation.ACCEPT,
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
    assert review.criteria.score == 4


def test_llm_reply_valid_recommendations():
    """Test that LLMReply accepts all valid Recommendation enum values."""
    for rec in Recommendation:
        criteria = LLMReply(
            novelty="n",
            methodology="m",
            results="r",
            clarity="c",
            impact="i",
            limitations="l",
            strengths="s",
            score=3,
            recommendation=rec,
            detailed_feedback="f",
        )
        assert criteria.recommendation == rec


def test_paper_review_raw_response_stored():
    """Test that the raw LLM response is stored on PaperReview."""
    criteria = LLMReply(
        novelty="n",
        methodology="m",
        results="r",
        clarity="c",
        impact="i",
        limitations="l",
        strengths="s",
        score=2,
        recommendation=Recommendation.REJECT,
        detailed_feedback="f",
    )
    review = PaperReview(
        paper_title="My Paper",
        reviewer_model="model-x",
        criteria=criteria,
        raw_response="raw json here",
    )
    assert review.raw_response == "raw json here"


# ---------------------------------------------------------------------------
# ReviewSystem (async review_paper)
# ---------------------------------------------------------------------------


import json


def test_review_system_review_paper():
    """Test ReviewSystem.review_paper with a mocked Ollama client."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from ollama import AsyncClient

    from sibyl.reviewer import ReviewSystem

    llm_reply_json = json.dumps(
        {
            "novelty": "Highly novel",
            "methodology": "Rigorous",
            "results": "Strong",
            "clarity": "Clear",
            "impact": "High",
            "limitations": "Minor",
            "strengths": "Many",
            "score": 4,
            "recommendation": "Accept",
            "detailed_feedback": "Excellent work",
        }
    )

    mock_response = MagicMock()
    mock_response.response = llm_reply_json

    mock_client = AsyncMock(spec=AsyncClient)
    mock_client.generate = AsyncMock(return_value=mock_response)

    reviewer = ReviewSystem(mock_client, "test-model")

    async def run():
        return await reviewer.review_paper("paper text content", "Test Paper Title", "test-model")

    review = asyncio.get_event_loop().run_until_complete(run())

    assert review.paper_title == "Test Paper Title"
    assert review.reviewer_model == "test-model"
    assert review.criteria.score == 4
    assert review.criteria.recommendation == Recommendation.ACCEPT
    assert review.raw_response == llm_reply_json


def test_review_system_empty_response_raises():
    """Test ReviewSystem.review_paper raises ValueError on empty LLM response."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from ollama import AsyncClient

    from sibyl.reviewer import ReviewSystem

    mock_response = MagicMock()
    mock_response.response = ""  # Empty response

    mock_client = AsyncMock(spec=AsyncClient)
    mock_client.generate = AsyncMock(return_value=mock_response)

    reviewer = ReviewSystem(mock_client, "test-model")

    async def run():
        return await reviewer.review_paper("paper text", "Title", "test-model")

    with pytest.raises(ValueError, match="empty response"):
        asyncio.get_event_loop().run_until_complete(run())
