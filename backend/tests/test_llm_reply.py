"""Tests for the LLMReply and Recommendation models."""

import pytest

from sibyl.config import MAX_SCORE
from sibyl.web.model.llm_reply import FormAwareLLMReply, LLMReply, Recommendation


def _make_reply(**kwargs) -> LLMReply:
    """Helper: build a minimal valid LLMReply, overriding any provided fields."""
    defaults = {
        "novelty": "Novel approach",
        "methodology": "Sound methodology",
        "results": "Strong results",
        "clarity": "Well-written",
        "impact": "High impact",
        "limitations": "Few limitations",
        "strengths": "Many strengths",
        "score": 3,
        "recommendation": Recommendation.ACCEPT,
        "detailed_feedback": "Good paper overall",
    }
    defaults.update(kwargs)
    return LLMReply(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Recommendation enum
# ---------------------------------------------------------------------------


def test_recommendation_accept_value():
    assert Recommendation.ACCEPT == "Accept"


def test_recommendation_minor_revision_value():
    assert Recommendation.MINOR_REVISION == "Minor Revision"


def test_recommendation_major_revision_value():
    assert Recommendation.MAJOR_REVISION == "Major Revision"


def test_recommendation_reject_value():
    assert Recommendation.REJECT == "Reject"


def test_recommendation_all_values():
    values = {r.value for r in Recommendation}
    assert values == {"Accept", "Minor Revision", "Major Revision", "Reject"}


# ---------------------------------------------------------------------------
# LLMReply model creation
# ---------------------------------------------------------------------------


def test_llm_reply_basic_creation():
    reply = _make_reply()
    assert reply.novelty == "Novel approach"
    assert reply.score == 3
    assert reply.recommendation == Recommendation.ACCEPT
    assert reply.review_form_response is None


def test_form_aware_reply_requires_completed_form():
    data = _make_reply().model_dump(exclude={"review_form_response"})

    with pytest.raises(ValueError):
        FormAwareLLMReply(**data)

    reply = FormAwareLLMReply(**data, review_form_response="# Completed form\n\nAnswer")
    assert reply.review_form_response.startswith("# Completed form")


def test_llm_reply_all_recommendations():
    for rec in Recommendation:
        reply = _make_reply(recommendation=rec, score=3)
        assert reply.recommendation == rec


def test_llm_reply_score_min_boundary():
    reply = _make_reply(score=1)
    assert reply.score == 1


def test_llm_reply_score_max_boundary():
    reply = _make_reply(score=MAX_SCORE)
    assert reply.score == MAX_SCORE


def test_llm_reply_score_too_low_raises():
    with pytest.raises(ValueError):
        _make_reply(score=0)


def test_llm_reply_score_too_high_raises():
    with pytest.raises(ValueError):
        _make_reply(score=MAX_SCORE + 1)


def test_llm_reply_invalid_recommendation_raises():
    with pytest.raises(ValueError):
        _make_reply(recommendation="Publish")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# model_json_schema (used by ReviewSystem for structured output)
# ---------------------------------------------------------------------------


def test_llm_reply_json_schema_contains_required_fields():
    schema = LLMReply.model_json_schema()
    assert "properties" in schema
    props = schema["properties"]
    for field in ("novelty", "methodology", "results", "clarity", "impact", "limitations", "strengths", "score", "recommendation", "detailed_feedback"):
        assert field in props, f"Field '{field}' missing from JSON schema"


def test_llm_reply_json_schema_score_constraints():
    schema = LLMReply.model_json_schema()
    score_prop = schema["properties"]["score"]
    assert score_prop.get("minimum") == 1 or score_prop.get("exclusiveMinimum") == 0
    assert score_prop.get("maximum") == MAX_SCORE


# ---------------------------------------------------------------------------
# model_dump / serialisation
# ---------------------------------------------------------------------------


def test_llm_reply_model_dump_roundtrip():
    reply = _make_reply(score=2, recommendation=Recommendation.REJECT)
    data = reply.model_dump()
    assert data["score"] == 2
    assert data["recommendation"] == "Reject"

    # Restore from dict
    restored = LLMReply(**data)
    assert restored.score == reply.score
    assert restored.recommendation == reply.recommendation


def test_llm_reply_model_validate_json():
    import json

    payload = {
        "novelty": "n",
        "methodology": "m",
        "results": "r",
        "clarity": "c",
        "impact": "i",
        "limitations": "l",
        "strengths": "s",
        "score": 4,
        "recommendation": "Minor Revision",
        "detailed_feedback": "f",
    }
    reply = LLMReply.model_validate_json(json.dumps(payload))
    assert reply.score == 4
    assert reply.recommendation == Recommendation.MINOR_REVISION
