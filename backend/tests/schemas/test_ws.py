"""WebSocket messages must carry everything their producers send."""

from sibyl.schemas.llm_reply import LLMReply, Recommendation
from sibyl.schemas.reviews import ReviewCriteria
from sibyl.schemas.ws import PullProgress, ReviewCompleted, ReviewResult, ReviewResults
from tests.schemas.test_responses import assert_keeps_fields


def test_pull_progress_passes_engine_fields_through() -> None:
    """Ollama's progress lines keep their extra fields (digest); missing counts go out as null, as the schema says."""
    part = {"status": "pulling abc", "digest": "sha256:abc", "total": 100, "completed": 40}
    assert PullProgress.model_validate(part).model_dump() == part
    assert PullProgress.model_validate({"status": "success"}).model_dump() == {"status": "success", "completed": None, "total": None}


def test_review_criteria_keeps_every_llm_reply_field() -> None:
    """The completed message's criteria keep every field the reviewer fills, conference answers included."""
    reply = LLMReply(score=1, recommendation=Recommendation.MINOR_REVISION, novelty="new", review_form_response="form", conference="neurips", review_form_answers={"q1": 3})
    assert_keeps_fields(ReviewCriteria, reply.model_dump(mode="json"))


def test_review_completed_serialises_recommendation_as_text() -> None:
    """The recommendation enum goes over the wire as its text."""
    reply = LLMReply(score=1, recommendation=Recommendation.ACCEPT)
    result = ReviewResult(paper_title="P", reviewer_model="m", criteria=ReviewCriteria.model_validate(reply.model_dump(mode="json")), raw_response="{}")
    message = ReviewCompleted(review_id="r1", results=ReviewResults(paper_title="P", reviews=[result])).model_dump(mode="json")
    assert message["status"] == "completed"
    assert message["results"]["reviews"][0]["criteria"]["recommendation"] == "Accept"
