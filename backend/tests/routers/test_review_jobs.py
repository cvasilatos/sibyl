"""Tests for submitting reviews to the queue: review forms, GPU choice and limits."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from sibyl.main import app
from sibyl.routers.review_jobs import _form
from sibyl.services.review_forms import MAX_REVIEW_FORM_BYTES

PDF = {"file": ("paper.pdf", b"%PDF-1.4", "application/pdf")}


def _decode(filename: str, content: bytes) -> str | None:
    return _form(None, None, (filename, content))[0]


@pytest.mark.parametrize("filename", ["review.txt", "review.md", "review.markdown", "REVIEW.MD"])
def test_decode_review_form(filename: str) -> None:
    """Decode every supported review-form extension as UTF-8 text."""
    form_content = "# Conference Review\n\n## Significance\n[Your answer]"
    assert _decode(filename, form_content.encode()) == form_content


def test_decode_review_form_strips_utf8_bom() -> None:
    """Allow common UTF-8 files that include a byte-order mark."""
    assert _decode("review.txt", b"\xef\xbb\xbfQuestion") == "Question"


@pytest.mark.parametrize(
    ("filename", "content", "status", "match"),
    [
        ("review.pdf", b"Questions", 400, "Review form must be"),
        ("review", b"Questions", 400, "Review form must be"),
        ("review.txt", b"  \n", 400, "cannot be empty"),
        ("review.txt", b"x" * (MAX_REVIEW_FORM_BYTES + 1), 413, "64 KiB or smaller"),
        ("review.md", b"\xff\xfe", 400, "valid UTF-8"),
    ],
)
def test_rejects_bad_review_forms(filename: str, content: bytes, status: int, match: str) -> None:
    """Unsupported, empty, oversized and binary forms are refused with a reason."""
    with pytest.raises(HTTPException, match=match) as error:
        _decode(filename, content)
    assert error.value.status_code == status


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_submit_queues_the_review(client: TestClient, held_queue) -> None:
    """A submitted review is queued with its settings, its paper kept until it runs."""
    response = client.post(
        "/api/review-jobs",
        files={**PDF, "review_form": ("form.md", b"# Q1", "text/markdown")},
        data={"model": "m", "gpu": "1", "vlm": "none", "related": "true", "sources": "arxiv", "detail": "concise", "mode": "sections"},
    )
    assert response.status_code == 200, response.text
    job = response.json()
    assert job["status"] == "queued"
    assert job["position"] == 1
    assert job["owner"] == "local"
    assert job["requested_gpu"] == 1
    assert job["form_name"] == "form.md"
    assert job["steps"] == ["parse", "related_work", "review", "save"]
    assert held_queue.pdf_path(job["id"]).read_bytes() == b"%PDF-1.4"
    settings = held_queue._jobs[job["id"]].settings
    assert (settings.review_form, settings.sources, settings.detail, settings.mode) == ("# Q1", ("arxiv",), "concise", "sections")

    listing = client.get("/api/review-jobs").json()
    assert listing["slots"] == 2
    assert [j["id"] for j in listing["jobs"]] == [job["id"]]


def test_submit_rejects_unknown_gpu_and_missing_model(client: TestClient, held_queue) -> None:
    """A GPU the queue does not schedule on, or no model, is refused and nothing is kept."""
    assert client.post("/api/review-jobs", files=PDF, data={"model": "m", "gpu": "7"}).status_code == 400
    assert client.post("/api/review-jobs", files=PDF, data={}).status_code == 422
    assert held_queue.visible_to(app_user()) == []
    assert not list(held_queue.directory.glob("*.pdf"))


def test_submit_limits_reviews_per_user(client: TestClient, held_queue, monkeypatch: pytest.MonkeyPatch) -> None:
    """One user cannot fill the queue."""
    monkeypatch.setenv("SIBYL_MAX_QUEUED_PER_USER", "2")
    for _ in range(2):
        assert client.post("/api/review-jobs", files=PDF, data={"model": "m"}).status_code == 200
    third = client.post("/api/review-jobs", files=PDF, data={"model": "m"})
    assert third.status_code == 429
    assert "already have 2" in third.json()["detail"]


def test_cancel_queued_then_dismiss(client: TestClient, held_queue) -> None:
    """Deleting a queued job cancels it; deleting it again removes it from the list."""
    job = client.post("/api/review-jobs", files=PDF, data={"model": "m"}).json()
    cancelled = client.delete(f"/api/review-jobs/{job['id']}").json()
    assert cancelled["status"] == "cancelled"
    assert not held_queue.pdf_path(job["id"]).exists()
    assert client.get(f"/api/review-jobs/{job['id']}").json()["status"] == "cancelled"
    assert client.delete(f"/api/review-jobs/{job['id']}").status_code == 200
    assert client.get(f"/api/review-jobs/{job['id']}").status_code == 404


def app_user():
    from sibyl.services.auth import local_user

    return local_user()
