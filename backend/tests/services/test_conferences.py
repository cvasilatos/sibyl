"""Tests for conference review templates and conference-mode reviews."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from sibyl.inference.ollama_engine import OllamaEngine
from sibyl.services.conferences import ConferenceTemplate, list_conferences, load_conferences
from sibyl.services.reviewer import FORM_TEMPERATURE, ReviewSystem, conference_schema

TEMPLATE = ConferenceTemplate.model_validate(
    {
        "id": "testconf",
        "name": "TestConf",
        "full_name": "Test Conference",
        "area": "Machine Learning",
        "edition": "2025",
        "guidelines": "Be constructive.",
        "questions": [
            {"id": "summary", "label": "Summary", "type": "text", "prompt": "Summarize the paper."},
            {
                "id": "soundness",
                "label": "Soundness",
                "type": "choice",
                "options": [{"value": 4, "label": "excellent"}, {"value": 3, "label": "good"}, {"value": 2, "label": "fair"}, {"value": 1, "label": "poor"}],
            },
            {"id": "decision", "label": "Decision", "type": "choice", "options": [{"value": "accept", "label": "Accept"}, {"value": "reject", "label": "Reject"}]},
        ],
    }
)

NORMALIZED = {"score": 4, "recommendation": "Accept"}


def test_template_schema_requires_every_question_on_official_scale():
    schema = TEMPLATE.json_schema()
    assert schema["required"] == ["summary", "soundness", "decision"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["soundness"] == {
        "type": "integer",
        "enum": [4, 3, 2, 1],
        "description": "Soundness. Scale: 4 = excellent; 3 = good; 2 = fair; 1 = poor",
    }
    assert schema["properties"]["decision"]["type"] == "string"
    assert schema["properties"]["summary"]["minLength"] == 1


def test_conference_schema_asks_only_for_the_form_score_and_recommendation():
    schema = conference_schema(TEMPLATE)
    assert list(schema["properties"]) == ["conference_review", "score", "recommendation"]
    assert schema["required"] == ["conference_review", "score", "recommendation"]
    assert "Recommendation" in schema["$defs"]


def test_normalize_answers_coerces_and_validates():
    assert TEMPLATE.normalize_answers({"summary": " ok ", "soundness": "3", "decision": "accept"}) == {"summary": "ok", "soundness": 3, "decision": "accept"}
    with pytest.raises(ValueError, match="missing answers for: decision"):
        TEMPLATE.normalize_answers({"summary": "x", "soundness": 3})
    with pytest.raises(ValueError, match="not a valid answer for Soundness"):
        TEMPLATE.normalize_answers({"summary": "x", "soundness": 7, "decision": "accept"})


def test_render_markdown_follows_form_order():
    md = TEMPLATE.render_markdown({"summary": "A paper.", "soundness": 3, "decision": "accept"})
    assert md.startswith("# TestConf 2025 Review")
    assert md.index("## Summary") < md.index("**Soundness:** 3 — good") < md.index("**Decision:** accept — Accept")


def test_review_with_conference_template():
    reply = {"conference_review": {"summary": "Solid work.", "soundness": 3, "decision": "accept"}, **NORMALIZED}
    client = AsyncMock()
    client.chat = AsyncMock(return_value=MagicMock(message=MagicMock(content=json.dumps(reply))))
    engine = OllamaEngine(hosts=["http://ollama.test:11434"])
    engine.clients = [client]

    review = asyncio.run(ReviewSystem(engine, "m").review_paper("paper text", "Title", "m", conference=TEMPLATE))

    assert client.chat.await_args is not None
    call = client.chat.await_args.kwargs
    assert "<conference_review_form>" in call["messages"][1]["content"]
    assert "Be constructive." in call["messages"][1]["content"]
    assert call["options"]["temperature"] == FORM_TEMPERATURE
    assert call["format"]["properties"]["conference_review"]["required"] == ["summary", "soundness", "decision"]
    assert review.criteria.conference == "testconf"
    assert review.criteria.review_form_answers == {"summary": "Solid work.", "soundness": 3, "decision": "accept"}
    assert "**Soundness:** 3 — good" in (review.criteria.review_form_response or "")
    assert review.criteria.score == 4
    assert review.criteria.novelty == ""
    assert review.criteria.detailed_feedback == ""
    assert "novelty" not in call["format"]["properties"]


def test_review_rejects_form_and_conference_together():
    engine = OllamaEngine(hosts=["http://ollama.test:11434"])
    with pytest.raises(ValueError, match="not both"):
        asyncio.run(ReviewSystem(engine, "m").review_paper("t", "T", "m", review_form="# Q", conference=TEMPLATE))


# --- bundled templates ----------------------------------------------------------------------------


def test_bundled_templates_are_valid():
    templates = load_conferences()
    for template in templates.values():
        schema = template.json_schema()
        assert schema["required"], template.id
        assert len(schema["required"]) == len(template.questions)
        for q in template.questions:
            if q.type == "choice":
                assert len({str(o.value) for o in q.options}) == len(q.options), f"{template.id}.{q.id} has duplicate values"


def test_bundled_templates_have_a_sourced_page_limit():
    for template in load_conferences().values():
        limit = template.page_limit
        assert limit is not None, f"{template.id} has no page_limit"
        assert limit.source_url.startswith("https://"), template.id
        assert limit.edition.isdigit(), template.id


def test_list_conferences_includes_page_limit():
    dac = next(c for c in list_conferences() if c["id"] == "dac")
    assert dac["page_limit"]["pages"] == 6


def test_list_conferences_is_sorted_by_area():
    from sibyl.services.conferences import AREA_ORDER

    ranks = [AREA_ORDER.index(c["area"]) if c["area"] in AREA_ORDER else len(AREA_ORDER) for c in list_conferences()]
    assert ranks == sorted(ranks)


# --- API ------------------------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch):
    from sibyl.main import app
    from sibyl.services import conferences

    monkeypatch.setattr(conferences, "load_conferences", lambda: {"testconf": TEMPLATE})
    app.state.engine = OllamaEngine(hosts=["http://ollama.test:11434"])
    return TestClient(app)


def test_conference_endpoints(client):
    listing = client.get("/api/conferences").json()
    assert listing["count"] == 1
    assert listing["conferences"][0]["id"] == "testconf"
    assert listing["conferences"][0]["question_count"] == 3

    detail = client.get("/api/conferences/testconf").json()
    assert [q["id"] for q in detail["questions"]] == ["summary", "soundness", "decision"]
    assert "Soundness" in detail["form_markdown"]
    assert client.get("/api/conferences/nope").status_code == 404


def test_upload_with_conference(client):
    from sibyl.state import review_sessions

    files = {"file": ("paper.pdf", b"%PDF-1.4", "application/pdf")}
    response = client.post("/api/upload", files=files, data={"conference_id": "testconf"})
    assert response.status_code == 200
    assert response.json()["conference_id"] == "testconf"
    assert review_sessions[response.json()["session_id"]]["conference_id"] == "testconf"

    assert client.post("/api/upload", files=files, data={"conference_id": "nope"}).status_code == 400
    both = {**files, "review_form": ("form.md", b"# Q", "text/markdown")}
    assert client.post("/api/upload", files=both, data={"conference_id": "testconf"}).status_code == 400


def test_engine_endpoint(client):
    data = client.get("/api/engine").json()
    assert data["name"] == "ollama"
    assert data["supports_downloads"] is True
    assert data["platform"]


def test_ws_review_session_with_conference(client, monkeypatch):
    """Full review flow over the WebSocket: upload with a conference, parse, generate, store."""
    from sibyl.routers import ws
    from sibyl.services.pdf_parser import PDFParser

    seen_slots: list[int] = []

    def fake_metadata(_self, slot):
        seen_slots.append(slot)
        return {"title": "A Paper", "text": "paper body"}

    monkeypatch.setattr(PDFParser, "get_metadata", fake_metadata)
    monkeypatch.setattr(ws.storage, "save_review", lambda **_kwargs: "review_123")

    reply = {"conference_review": {"summary": "Fine.", "soundness": 2, "decision": "reject"}, **NORMALIZED}
    ollama = AsyncMock()
    ollama.chat = AsyncMock(return_value=MagicMock(message=MagicMock(content=json.dumps(reply))))
    client.app.state.engine.clients = [ollama]

    upload = client.post("/api/upload", files={"file": ("p.pdf", b"%PDF-1.4", "application/pdf")}, data={"conference_id": "testconf"}).json()

    messages = []
    with client.websocket_connect(f"/ws/session/{upload['session_id']}?model=m&host=0") as ws:
        while True:
            message = ws.receive_json()
            messages.append(message)
            if message["status"] in {"completed", "error"}:
                break

    final = messages[-1]
    assert final["status"] == "completed", final
    assert final["review_id"] == "review_123"
    criteria = final["results"]["reviews"][0]["criteria"]
    assert criteria["conference"] == "testconf"
    assert criteria["review_form_answers"]["soundness"] == 2
    assert any("TestConf 2025 reviewer form" in m.get("message", "") for m in messages)
    assert seen_slots == [0]
