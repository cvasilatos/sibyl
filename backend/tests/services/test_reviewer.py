"""Tests for the reviewer module."""

import json

import pytest
from pydantic import ValidationError

from sibyl.schemas.llm_reply import LLMReply, Recommendation
from sibyl.services.reviewer import PaperReview, ReviewCriteria


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
    with pytest.raises(ValidationError, match="score"):
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
    with pytest.raises(ValidationError, match="score"):
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


def _engine_with(mock_client):
    """Ollama engine whose single host is a mocked AsyncClient."""
    from sibyl.inference.ollama_engine import OllamaEngine

    engine = OllamaEngine(hosts=["http://ollama.test:11434"])
    engine.clients = [mock_client]
    return engine


def test_review_system_review_paper():
    """Test ReviewSystem.review_paper with a mocked Ollama client."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from ollama import AsyncClient

    from sibyl.services.reviewer import ReviewSystem

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
    mock_response.message.content = llm_reply_json

    mock_client = AsyncMock(spec=AsyncClient)
    mock_client.chat = AsyncMock(return_value=mock_response)

    reviewer = ReviewSystem(_engine_with(mock_client), "test-model")

    async def run():
        return await reviewer.review_paper("paper text content", "Test Paper Title", "test-model")

    review = asyncio.run(run())

    assert review.paper_title == "Test Paper Title"
    assert review.reviewer_model == "test-model"
    assert review.criteria.score == 4
    assert review.criteria.recommendation == Recommendation.ACCEPT
    assert review.raw_response == llm_reply_json
    call = mock_client.chat.await_args
    assert call is not None
    schema = call.kwargs["format"]
    assert "detailed_feedback" in schema["required"]
    assert "review_form_response" not in schema["properties"]


def test_review_system_empty_response_raises():
    """Test ReviewSystem.review_paper raises ValueError on empty LLM response."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from ollama import AsyncClient

    from sibyl.services.reviewer import ReviewSystem

    mock_response = MagicMock()
    mock_response.message.content = ""  # Empty response

    mock_client = AsyncMock(spec=AsyncClient)
    mock_client.chat = AsyncMock(return_value=mock_response)

    reviewer = ReviewSystem(_engine_with(mock_client), "test-model")

    async def run():
        return await reviewer.review_paper("paper text", "Title", "test-model")

    with pytest.raises(ValueError, match="empty response"):
        asyncio.run(run())


def test_review_system_completes_custom_review_form():
    """Test that custom forms use the strict form schema and lower temperature."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from ollama import AsyncClient

    from sibyl.services.reviewer import FORM_TEMPERATURE, ReviewSystem

    response_data = {
        "review_form_response": "# Significance\n\nThe work is significant.",
        "score": 4,
        "recommendation": "Accept",
    }
    mock_response = MagicMock(message=MagicMock(content=json.dumps(response_data)))
    mock_client = AsyncMock(spec=AsyncClient)
    mock_client.chat = AsyncMock(return_value=mock_response)
    reviewer = ReviewSystem(_engine_with(mock_client), "test-model")

    async def run():
        return await reviewer.review_paper(
            "paper text",
            "Paper title",
            "test-model",
            review_form="# Significance\n[Answer here]",
        )

    review = asyncio.run(run())
    assert mock_client.chat.await_args is not None
    call = mock_client.chat.await_args.kwargs

    assert review.criteria.review_form_response == response_data["review_form_response"]
    assert "<review_form>\n# Significance" in call["messages"][1]["content"]
    assert "<research_paper>\npaper text" in call["messages"][1]["content"]
    assert call["messages"][0]["content"]
    assert call["options"]["temperature"] == FORM_TEMPERATURE
    assert call["format"]["required"] == ["review_form_response", "score", "recommendation"]
    assert "novelty" not in call["format"]["properties"]
    assert review.criteria.novelty == ""


# ---------------------------------------------------------------------------
# Review length and section-by-section mode
# ---------------------------------------------------------------------------


DEFAULT_REPLY = {
    "novelty": "n",
    "methodology": "m",
    "results": "r",
    "clarity": "c",
    "impact": "i",
    "limitations": "l",
    "strengths": "s",
    "score": 4,
    "recommendation": "Accept",
    "detailed_feedback": "1. f",
}


def _schema_driven_client():
    """Mocked Ollama client that answers each call with the fields its schema asks for."""
    from unittest.mock import AsyncMock, MagicMock

    from ollama import AsyncClient

    def answer(**kwargs):
        properties = kwargs["format"]["properties"]
        return MagicMock(message=MagicMock(content=json.dumps({name: DEFAULT_REPLY.get(name, f"answer {name}") for name in properties})))

    client = AsyncMock(spec=AsyncClient)
    client.chat = AsyncMock(side_effect=answer)
    return client


@pytest.mark.parametrize("detail", ["auto", "concise", "standard", "detailed"])
def test_detail_level_steers_length_in_the_prompt_without_a_token_limit(detail):
    import asyncio

    from sibyl.schemas.review_config import ReviewDetail, ReviewMode
    from sibyl.services.reviewer import ReviewSystem, length_guidance

    client = _schema_driven_client()
    engine = _engine_with(client)
    review = asyncio.run(ReviewSystem(engine, "m").review_paper("paper text", "T", "m", detail=ReviewDetail(detail), mode=ReviewMode.SINGLE))

    call = client.chat.await_args.kwargs
    assert length_guidance(ReviewDetail(detail)) in call["messages"][1]["content"]
    assert ("Length:" in call["messages"][1]["content"]) == (detail != "auto")
    # The output cap is the rest of the context window, not a configured number.
    assert call["options"]["num_ctx"] == engine.context_length("m")  # the mocked show() reports no limit
    assert call["options"]["num_predict"] > 8192
    assert review.config is not None
    assert review.config.detail == detail
    assert review.config.mode == "single"
    assert review.config.generation_calls == 1
    assert review.config.form == "default"


def test_sections_mode_writes_one_section_per_call_then_scores():
    import asyncio

    from sibyl.inference.ollama_engine import KEEP_LOADED
    from sibyl.schemas.llm_reply import NARRATIVE_FIELDS
    from sibyl.schemas.review_config import ReviewDetail, ReviewMode
    from sibyl.services.reviewer import ReviewSystem

    client = _schema_driven_client()
    statuses: list[str] = []

    progress: list[tuple[int, int]] = []

    async def on_status(message: str) -> None:
        statuses.append(message)

    async def on_progress(done: int, planned: int) -> None:
        progress.append((done, planned))

    review = asyncio.run(
        ReviewSystem(_engine_with(client), "m").review_paper(
            "paper text", "T", "m", detail=ReviewDetail.DETAILED, mode=ReviewMode.SECTIONS, on_status=on_status, on_progress=on_progress
        )
    )

    calls = [c.kwargs for c in client.chat.await_args_list]
    assert [list(c["format"]["properties"]) for c in calls] == [[name] for name in NARRATIVE_FIELDS] + [["score", "recommendation"]]
    # Later calls see the sections already written; the model stays loaded until the last call.
    assert "<your_review_so_far>" not in calls[0]["messages"][1]["content"]
    assert "## Novelty\nn" in calls[1]["messages"][1]["content"]
    assert all(c["keep_alive"] == KEEP_LOADED for c in calls[:-1])
    assert calls[-1]["keep_alive"] != KEEP_LOADED
    assert "numbered list" in calls[NARRATIVE_FIELDS.index("detailed_feedback")]["messages"][1]["content"]
    assert statuses[0].startswith("Section 1/9")
    total = len(NARRATIVE_FIELDS) + 1
    assert progress == [(done, total) for done in range(total)]  # reported before each call
    assert review.criteria.methodology == "m"
    assert review.criteria.score == 4
    assert "--- novelty ---" in review.raw_response
    assert review.config is not None
    assert review.config.mode == "sections"
    assert review.config.generation_calls == len(NARRATIVE_FIELDS) + 1


def test_sections_mode_answers_conference_questions_one_by_one():
    import asyncio

    from sibyl.schemas.review_config import ReviewMode
    from sibyl.services.reviewer import ReviewSystem
    from tests.services.test_conferences import TEMPLATE

    client = _schema_driven_client()
    calls_answers = {"soundness": 3, "decision": "accept"}
    DEFAULT_REPLY.update(calls_answers)
    try:
        review = asyncio.run(ReviewSystem(_engine_with(client), "m").review_paper("paper text", "T", "m", conference=TEMPLATE, mode=ReviewMode.SECTIONS))
    finally:
        for key in calls_answers:
            DEFAULT_REPLY.pop(key)

    calls = [c.kwargs for c in client.chat.await_args_list]
    assert [list(c["format"]["properties"]) for c in calls] == [["summary"], ["soundness", "decision", "score", "recommendation"]]
    assert review.criteria.review_form_answers == {"summary": "answer summary", "soundness": 3, "decision": "accept"}
    assert review.config is not None
    assert review.config.form == "conference"
    assert review.config.conference == "TestConf 2025"


def test_sections_mode_falls_back_to_one_pass_for_custom_forms():
    import asyncio

    from sibyl.schemas.review_config import ReviewMode
    from sibyl.services.reviewer import ReviewSystem

    DEFAULT_REPLY["review_form_response"] = "# Q\nA"
    try:
        client = _schema_driven_client()
        review = asyncio.run(ReviewSystem(_engine_with(client), "m").review_paper("paper text", "T", "m", review_form="# Q", mode=ReviewMode.SECTIONS))
    finally:
        DEFAULT_REPLY.pop("review_form_response")

    assert client.chat.await_count == 1
    assert review.config is not None
    assert review.config.mode == "single"
    assert review.config.form == "custom"
