"""Sign-in with the server's own accounts (PAM), limited to one Unix group, and signed session cookies.

``SIBYL_AUTH=pam`` checks usernames and passwords with PAM, the way SSH and the console do, so on a machine joined
to a directory (SSSD, LDAP, Active Directory) users sign in with the password they use for the server. Only members
of ``SIBYL_AUTH_GROUP`` may sign in; ``SIBYL_ADMIN_USERS`` may manage everyone's reviews and forms. The backend must
run on the host (not in a container) to reach PAM and the directory.

``SIBYL_AUTH=none`` (the default, for a single-user install) signs everyone in as the admin user ``local``.
"""

from __future__ import annotations

import base64
import grp
import hashlib
import hmac
import json
import logging
import os
import pwd
import re
import secrets
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sibyl import config

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

SESSION_COOKIE = "sibyl_session"
LOCAL_USER = "local"
"""The only user when sign-in is off; an admin, so it can manage reviews saved before users existed."""
DEFAULT_SESSION_HOURS = 12.0
MAX_FAILURES = 5
"""Failed sign-ins allowed per user (and per client address) within ``FAILURE_WINDOW`` before further tries are refused.
Every try reaches the directory, which may lock the account after a few failures; this stops guessing well before."""
FAILURE_WINDOW = 15 * 60.0
_USERNAME = re.compile(r"^[A-Za-z0-9._@-]{1,64}$")


@dataclass(frozen=True, slots=True)
class User:
    """A signed-in user."""

    username: str
    is_admin: bool

    def can_manage(self, owner: str | None) -> bool:
        """Whether this user may delete or cancel something owned by ``owner`` (``None``: saved before users existed)."""
        return self.is_admin or (owner is not None and owner == self.username)


def auth_enabled() -> bool:
    """Return True when users sign in with PAM (``SIBYL_AUTH=pam``); read on each call so tests can switch it."""
    mode = os.getenv("SIBYL_AUTH", "none").strip().lower()
    if mode not in {"none", "pam"}:
        raise ValueError(f"SIBYL_AUTH must be 'none' or 'pam', not {mode!r}")
    return mode == "pam"


def admin_users() -> set[str]:
    """Usernames listed in ``SIBYL_ADMIN_USERS`` (comma separated)."""
    return {name.strip() for name in os.getenv("SIBYL_ADMIN_USERS", "").split(",") if name.strip()}


def local_user() -> User:
    """Return the user everyone is when sign-in is off."""
    return User(LOCAL_USER, is_admin=True)


def user_for(username: str) -> User:
    """Return the signed-in ``username`` with their role."""
    return User(username, is_admin=username in admin_users())


def session_seconds() -> float:
    """How long a sign-in lasts (``SIBYL_SESSION_HOURS``, 12 by default)."""
    try:
        hours = float(os.getenv("SIBYL_SESSION_HOURS", str(DEFAULT_SESSION_HOURS)))
    except ValueError:
        hours = DEFAULT_SESSION_HOURS
    return max(hours, 0.01) * 3600


# --- Accounts -----------------------------------------------------------------------------------------------------


def canonical_username(username: str) -> str | None:
    """Return the account's name as the system spells it (directories often accept other capitalizations), or None if unknown."""
    if not _USERNAME.fullmatch(username):
        return None
    try:
        return pwd.getpwnam(username).pw_name
    except KeyError:
        return None


def in_group(username: str, group: str) -> bool:
    """Whether ``username`` belongs to ``group``, as primary or supplementary group.

    Uses the user's group list rather than the group's member list, which directory groups usually leave empty.
    """
    try:
        gid = grp.getgrnam(group).gr_gid
        account = pwd.getpwnam(username)
    except KeyError:
        return False
    return gid in os.getgrouplist(account.pw_name, account.pw_gid)


def check_password(username: str, password: str) -> bool:
    """Ask PAM (service ``SIBYL_PAM_SERVICE``, ``login`` by default) whether the password is right. Blocks."""
    import pam  # noqa: PLC0415  (only needed with SIBYL_AUTH=pam)

    service = os.getenv("SIBYL_PAM_SERVICE", "login")
    checker = pam.pam()
    if checker.authenticate(username, password, service=service, resetcreds=False):
        return True
    logger.info("PAM rejected %s: %s", username, checker.reason)
    return False


def authenticate(username: str, password: str) -> User | None:
    """Return the user for valid credentials of a member of ``SIBYL_AUTH_GROUP``, else None. Blocks (PAM may be slow)."""
    group = os.getenv("SIBYL_AUTH_GROUP", "").strip()
    if not group:
        raise RuntimeError("SIBYL_AUTH=pam needs SIBYL_AUTH_GROUP: the Unix group whose members may sign in")
    name = canonical_username(username.strip())
    if name is None or not password:
        return None
    if not in_group(name, group):  # checked first: non-members never reach PAM, so their accounts cannot be locked
        logger.info("Sign-in refused for %s: not in group %s", name, group)
        return None
    if not check_password(name, password):
        return None
    return user_for(name)


class LoginThrottle:
    """Refuse sign-in for a user or client address after ``MAX_FAILURES`` failures within ``FAILURE_WINDOW``."""

    def __init__(self, max_failures: int = MAX_FAILURES, window: float = FAILURE_WINDOW) -> None:
        """Start with no failures recorded."""
        self.max_failures = max_failures
        self.window = window
        self._failures: dict[str, list[float]] = {}

    def _recent(self, key: str, now: float) -> list[float]:
        times = [t for t in self._failures.get(key, []) if now - t < self.window]
        if times:
            self._failures[key] = times
        else:
            self._failures.pop(key, None)
        return times

    def retry_after(self, *keys: str) -> float:
        """Seconds until any of ``keys`` may try again (0 when all may)."""
        now = time.monotonic()
        wait = 0.0
        for key in keys:
            times = self._recent(key, now)
            if len(times) >= self.max_failures:
                wait = max(wait, self.window - (now - times[0]))
        return wait

    def failed(self, *keys: str) -> None:
        """Record a failed sign-in for each key."""
        now = time.monotonic()
        for key in keys:
            self._failures.setdefault(key, []).append(now)

    def succeeded(self, *keys: str) -> None:
        """Forget the failures of each key."""
        for key in keys:
            self._failures.pop(key, None)


# --- Session tokens -----------------------------------------------------------------------------------------------


def _secret_path() -> Path:
    return config.STORAGE_PATH / ".session_secret"


def secret_key() -> bytes:
    """``SIBYL_SECRET_KEY``, or a random key kept in the storage directory so sign-ins survive restarts."""
    configured = os.getenv("SIBYL_SECRET_KEY", "")
    if configured:
        return configured.encode()
    path = _secret_path()
    if path.is_file():
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # readable by the server's account only
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return key


def _sign(payload: bytes) -> str:
    return base64.urlsafe_b64encode(hmac.new(secret_key(), payload, hashlib.sha256).digest()).decode().rstrip("=")


def create_token(username: str, now: float | None = None) -> str:
    """Create a signed token naming ``username`` that expires after ``session_seconds``."""
    expires = (now if now is not None else time.time()) + session_seconds()
    payload = base64.urlsafe_b64encode(json.dumps({"u": username, "exp": expires}).encode()).decode().rstrip("=")
    return f"{payload}.{_sign(payload.encode())}"


def read_token(token: str, now: float | None = None) -> str | None:
    """Return the username in a valid, unexpired token, else None."""
    payload, _, signature = token.partition(".")
    if not payload or not hmac.compare_digest(signature, _sign(payload.encode())):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        username, expires = str(data["u"]), float(data["exp"])
    except (ValueError, KeyError, TypeError):
        return None
    if expires < (now if now is not None else time.time()):
        return None
    return username


def user_from_token(token: str | None) -> User | None:
    """Return the signed-in user for a session cookie, or the local user when sign-in is off."""
    if not auth_enabled():
        return local_user()
    username = read_token(token) if token else None
    if username is None:
        return None
    group = os.getenv("SIBYL_AUTH_GROUP", "").strip()
    if group and not in_group(username, group):  # removed from the group since signing in
        return None
    return user_for(username)


def secure_cookies() -> bool:
    """Mark the session cookie HTTPS-only (``SIBYL_SECURE_COOKIES``), for a backend behind a TLS proxy."""
    return os.getenv("SIBYL_SECURE_COOKIES", "").strip().lower() in {"1", "true", "yes"}
