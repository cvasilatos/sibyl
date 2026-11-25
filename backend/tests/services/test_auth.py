"""Sign-in with server accounts: group membership, session tokens and throttling of failed tries."""

import grp
import os
import pwd

import pytest

from sibyl import config
from sibyl.services import auth
from sibyl.services.auth import LoginThrottle, User


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "STORAGE_PATH", tmp_path)
    monkeypatch.delenv("SIBYL_SECRET_KEY", raising=False)
    return tmp_path


def test_can_manage() -> None:
    alice = User("alice", is_admin=False)
    assert alice.can_manage("alice")
    assert not alice.can_manage("bob")
    assert not alice.can_manage(None)  # saved before users existed: admins only
    assert User("root", is_admin=True).can_manage(None)


def test_auth_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIBYL_AUTH", raising=False)
    assert not auth.auth_enabled()
    assert auth.user_from_token(None) == User("local", is_admin=True)
    monkeypatch.setenv("SIBYL_AUTH", "PAM")
    assert auth.auth_enabled()
    assert auth.user_from_token(None) is None
    monkeypatch.setenv("SIBYL_AUTH", "ldap")
    with pytest.raises(ValueError, match="none' or 'pam"):
        auth.auth_enabled()


def test_tokens_round_trip_and_expire(monkeypatch: pytest.MonkeyPatch, storage) -> None:
    monkeypatch.setenv("SIBYL_SESSION_HOURS", "1")
    token = auth.create_token("alice", now=1000.0)
    assert auth.read_token(token, now=1000.0 + 3599) == "alice"
    assert auth.read_token(token, now=1000.0 + 3601) is None
    payload, _, signature = token.partition(".")
    forged = auth.create_token("bob", now=1000.0).partition(".")[0]
    assert auth.read_token(f"{forged}.{signature}", now=1000.0) is None
    assert auth.read_token(f"{payload}.", now=1000.0) is None
    assert auth.read_token("garbage", now=1000.0) is None
    # The generated key is kept, readable by the server's account only, so sign-ins survive restarts.
    key_file = storage / ".session_secret"
    assert oct(key_file.stat().st_mode & 0o777) == "0o600"
    assert auth.read_token(token, now=1000.0) == "alice"
    monkeypatch.setenv("SIBYL_SECRET_KEY", "another key")
    assert auth.read_token(token, now=1000.0) is None


def test_tokens_stop_working_when_removed_from_the_group(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIBYL_AUTH", "pam")
    monkeypatch.setenv("SIBYL_AUTH_GROUP", "lab")
    monkeypatch.setenv("SIBYL_ADMIN_USERS", "alice, carol")
    members = {"alice"}
    monkeypatch.setattr(auth, "in_group", lambda user, group: group == "lab" and user in members)
    token = auth.create_token("alice")
    assert auth.user_from_token(token) == User("alice", is_admin=True)
    members.clear()
    assert auth.user_from_token(token) is None


def test_in_group_uses_the_users_group_list() -> None:
    me = pwd.getpwuid(os.getuid())
    primary = grp.getgrgid(me.pw_gid).gr_name
    assert auth.in_group(me.pw_name, primary)
    assert not auth.in_group(me.pw_name, "no-such-group-sibyl")
    assert not auth.in_group("no-such-user-sibyl", primary)


def test_authenticate_checks_group_before_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIBYL_AUTH_GROUP", "lab")
    monkeypatch.setenv("SIBYL_ADMIN_USERS", "")
    monkeypatch.setattr(auth, "canonical_username", {"alice": "alice", "ALICE": "alice", "bob": "bob"}.get)
    monkeypatch.setattr(auth, "in_group", lambda user, _group: user == "alice")
    tried: list[str] = []

    def check_password(user: str, password: str) -> bool:
        tried.append(user)
        return password == "secret"  # noqa: S105

    monkeypatch.setattr(auth, "check_password", check_password)
    assert auth.authenticate(" ALICE ", "secret") == User("alice", is_admin=False)
    assert auth.authenticate("alice", "wrong") is None
    assert auth.authenticate("bob", "secret") is None  # not in the group
    assert auth.authenticate("nobody", "secret") is None
    assert auth.authenticate("alice", "") is None
    assert tried == ["alice", "alice"]  # non-members and unknown names never reach PAM

    monkeypatch.delenv("SIBYL_AUTH_GROUP")
    with pytest.raises(RuntimeError, match="SIBYL_AUTH_GROUP"):
        auth.authenticate("alice", "secret")


def test_canonical_username_rejects_odd_names() -> None:
    me = pwd.getpwuid(os.getuid()).pw_name
    assert auth.canonical_username(me) == me
    assert auth.canonical_username("../etc") is None
    assert auth.canonical_username("a b") is None
    assert auth.canonical_username("no-such-user-sibyl") is None


def test_throttle_blocks_after_repeated_failures() -> None:
    throttle = LoginThrottle(max_failures=2, window=60)
    assert throttle.retry_after("user:a", "ip:1") == 0
    throttle.failed("user:a", "ip:1")
    assert throttle.retry_after("user:a") == 0
    throttle.failed("user:a", "ip:1")
    assert 0 < throttle.retry_after("user:a") <= 60
    assert throttle.retry_after("ip:1") > 0
    assert throttle.retry_after("user:b") == 0
    throttle.succeeded("user:a")
    assert throttle.retry_after("user:a") == 0
