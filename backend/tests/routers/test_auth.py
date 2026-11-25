"""Signing in and what each user may do: everyone sees everything, but manages only their own reviews and forms."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sibyl import config
from sibyl.main import app
from sibyl.routers import auth as auth_router, reviews as reviews_router
from sibyl.services import auth
from sibyl.services.auth import LoginThrottle, User

PASSWORDS = {"alice": "a-pass", "bob": "b-pass", "root": "r-pass"}


@pytest.fixture
def pam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sign-in on, with three group members (root is an admin) and a fresh throttle."""
    monkeypatch.setattr(config, "STORAGE_PATH", tmp_path)
    monkeypatch.setenv("SIBYL_AUTH", "pam")
    monkeypatch.setenv("SIBYL_AUTH_GROUP", "lab")
    monkeypatch.setenv("SIBYL_ADMIN_USERS", "root")
    monkeypatch.setattr(auth, "canonical_username", lambda name: name if name in PASSWORDS or name == "mallory" else None)
    monkeypatch.setattr(auth, "in_group", lambda user, _group: user in PASSWORDS)
    monkeypatch.setattr(auth, "check_password", lambda user, password: PASSWORDS.get(user) == password)
    monkeypatch.setattr(auth_router, "throttle", LoginThrottle(max_failures=3, window=60))


def signed_in(username: str) -> TestClient:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": username, "password": PASSWORDS[username]})
    assert response.status_code == 200, response.text
    return client


def test_everything_but_health_needs_sign_in(pam, held_queue) -> None:
    client = TestClient(app)
    for path in ("/api/reviews", "/api/review-jobs", "/api/review-forms", "/api/conferences", "/api/gpu", "/api/statistics", "/api/auth/me"):
        assert client.get(path).status_code == 401, path
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/config").status_code == 200
    with client.websocket_connect("/ws/pull?model_name=x") as ws:
        assert ws.receive_json() == {"status": "error", "message": "Sign in to download models"}


def test_sign_in_and_out(pam) -> None:
    client = signed_in("alice")
    assert client.get("/api/auth/me").json() == {"username": "alice", "is_admin": False, "auth_enabled": True}
    cookie = client.cookies.get(auth.SESSION_COOKIE)
    assert cookie
    assert "httponly" in client.post("/api/auth/logout").headers["set-cookie"].lower()
    assert client.get("/api/auth/me").status_code == 401
    assert signed_in("root").get("/api/auth/me").json()["is_admin"] is True


def test_wrong_password_and_throttling(pam) -> None:
    client = TestClient(app)
    for _ in range(3):
        response = client.post("/api/auth/login", json={"username": "mallory", "password": "guess"})
        assert response.status_code == 401
    blocked = client.post("/api/auth/login", json={"username": "alice", "password": PASSWORDS["alice"]})
    assert blocked.status_code == 429  # same client address
    assert "Too many failed sign-ins" in blocked.json()["detail"]


def test_without_sign_in_everyone_is_the_local_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIBYL_AUTH", raising=False)
    client = TestClient(app)
    assert client.get("/api/auth/me").json() == {"username": "local", "is_admin": True, "auth_enabled": False}
    assert client.post("/api/auth/login", json={"username": "x", "password": "y"}).json()["username"] == "local"


def test_only_the_owner_or_an_admin_deletes_a_review(pam, monkeypatch: pytest.MonkeyPatch) -> None:
    reviews = {"r1": {"owner": "alice"}, "legacy": {"owner": None}}
    deleted: list[str] = []
    monkeypatch.setattr(reviews_router.storage, "get_review", reviews.get)
    monkeypatch.setattr(reviews_router.storage, "delete_review", lambda review_id: deleted.append(review_id) or True)
    owners: list[str | None] = []
    monkeypatch.setattr(reviews_router.storage, "delete_all_reviews", lambda owner=None: owners.append(owner) or 0)

    bob, alice, root = signed_in("bob"), signed_in("alice"), signed_in("root")
    assert bob.delete("/api/reviews/r1").status_code == 403
    assert alice.delete("/api/reviews/legacy").status_code == 403
    assert alice.delete("/api/reviews/r1").status_code == 200
    assert root.delete("/api/reviews/legacy").status_code == 200
    assert bob.delete("/api/reviews/missing").status_code == 404
    assert deleted == ["r1", "legacy"]

    bob.delete("/api/reviews")
    root.delete("/api/reviews")
    assert owners == ["bob", None]  # a user's "delete all" deletes their own; an admin's deletes everything


def test_only_the_owner_or_an_admin_deletes_a_form(pam) -> None:
    alice, bob, root = signed_in("alice"), signed_in("bob"), signed_in("root")
    files = {"file": ("f.md", b"# Q", "text/markdown")}
    first = alice.post("/api/review-forms", data={"name": "Mine"}, files=files).json()
    second = alice.post("/api/review-forms", data={"name": "Also mine"}, files=files).json()
    assert first["owner"] == "alice"
    assert [f["owner"] for f in bob.get("/api/review-forms").json()["forms"]] == ["alice", "alice"]  # everyone sees them
    assert bob.delete(f"/api/review-forms/{first['id']}").status_code == 403
    assert alice.delete(f"/api/review-forms/{first['id']}").status_code == 200
    assert root.delete(f"/api/review-forms/{second['id']}").status_code == 200


def test_only_admins_delete_models(pam) -> None:
    response = signed_in("alice").delete("/api/models/llama3")
    assert response.status_code == 403


def test_jobs_are_owned_by_who_submitted_them(pam, held_queue) -> None:
    alice, bob = signed_in("alice"), signed_in("bob")
    job = alice.post("/api/review-jobs", data={"model": "m"}, files={"file": ("p.pdf", b"%PDF", "application/pdf")}).json()
    assert job["owner"] == "alice"
    assert [j["id"] for j in bob.get("/api/review-jobs").json()["jobs"]] == [job["id"]]  # the queue is visible to all
    assert bob.delete(f"/api/review-jobs/{job['id']}").status_code == 403
    assert alice.delete(f"/api/review-jobs/{job['id']}").json()["status"] == "cancelled"
    assert held_queue.visible_to(User("bob", is_admin=False)) == []
