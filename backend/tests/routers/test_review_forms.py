"""Tests for saved custom review forms and their use in uploads."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sibyl import config
from sibyl.main import app
from sibyl.services import review_forms

FORM = "# Workshop Review\n\n## Strengths\n[Your answer]\n"


@pytest.fixture(autouse=True)
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep saved forms in a temporary storage directory."""
    monkeypatch.setattr(config, "STORAGE_PATH", tmp_path)
    return tmp_path


@pytest.fixture
def client() -> TestClient:
    """Client without the lifespan, so no inference engine is started."""
    return TestClient(app)


def save(client: TestClient, name: str, content: str = FORM, filename: str = "form.md") -> dict:
    response = client.post("/api/review-forms", data={"name": name}, files={"file": (filename, content.encode(), "text/markdown")})
    return {"status": response.status_code, **response.json()}


def test_save_list_get_delete(client: TestClient, storage: Path) -> None:
    """A saved form is listed by name, returned with its text, and can be deleted."""
    saved = save(client, "  My   Workshop ")
    assert saved["status"] == 200
    assert saved["name"] == "My Workshop"
    assert (storage / "review_forms" / f"{saved['id']}.json").is_file()

    listing = client.get("/api/review-forms").json()
    assert listing["count"] == 1
    assert listing["forms"][0] == {"id": saved["id"], "name": "My Workshop", "filename": "form.md", "created_at": saved["created_at"], "size": len(FORM.encode()), "owner": "local"}

    assert client.get(f"/api/review-forms/{saved['id']}").json()["content"] == FORM

    assert client.delete(f"/api/review-forms/{saved['id']}").status_code == 200
    assert client.get("/api/review-forms").json()["count"] == 0
    assert client.delete(f"/api/review-forms/{saved['id']}").status_code == 404


def test_names_are_unique_ignoring_case(client: TestClient) -> None:
    """A second form cannot reuse a name."""
    save(client, "Workshop")
    duplicate = save(client, "workshop")
    assert duplicate["status"] == 409
    assert "already exists" in duplicate["detail"]


@pytest.mark.parametrize(("name", "filename", "content"), [(" ", "f.md", FORM), ("x", "f.pdf", FORM), ("x", "f.md", " \n"), ("x" * 101, "f.md", FORM)])
def test_rejects_bad_forms(client: TestClient, name: str, filename: str, content: str) -> None:
    """Blank or overlong names and invalid files are refused."""
    assert save(client, name, content, filename)["status"] == 400


@pytest.mark.parametrize("form_id", ["../../etc/passwd", "not-a-hex-id", "A" * 32])
def test_ids_never_leave_the_store(form_id: str) -> None:
    """Ids that are not our hex ids never resolve to a file."""
    assert review_forms.get_form(form_id) is None
    assert review_forms.delete_form(form_id) is False


def test_submit_with_saved_form(client: TestClient, held_queue) -> None:
    """A review naming a saved form answers that form's text."""
    saved = save(client, "Workshop")
    response = client.post("/api/review-jobs", data={"review_form_id": saved["id"], "model": "m"}, files={"file": ("paper.pdf", b"%PDF", "application/pdf")})
    assert response.status_code == 200
    body = response.json()
    assert body["form_name"] == "Workshop"
    settings = held_queue._jobs[body["id"]].settings
    assert (settings.review_form, settings.review_form_filename) == (FORM, "Workshop")


def test_submit_rejects_unknown_or_combined_forms(client: TestClient, held_queue) -> None:
    """An unknown saved form, or more than one kind of form, is refused."""
    pdf = {"file": ("paper.pdf", b"%PDF", "application/pdf")}
    assert client.post("/api/review-jobs", data={"review_form_id": "0" * 32, "model": "m"}, files=pdf).status_code == 400
    saved = save(client, "Workshop")
    both = client.post("/api/review-jobs", data={"review_form_id": saved["id"], "conference_id": "neurips", "model": "m"}, files=pdf)
    assert both.status_code == 400
    assert "only one" in both.json()["detail"]
