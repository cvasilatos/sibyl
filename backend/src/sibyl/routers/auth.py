"""Sign-in, sign-out and the signed-in user; the ``CurrentUser`` dependency every other route uses."""

from typing import Annotated

from anyio import to_thread
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.requests import HTTPConnection

from sibyl.schemas.auth import CurrentUser, LoggedOut, LoginRequest
from sibyl.services import auth
from sibyl.services.auth import SESSION_COOKIE, LoginThrottle, User

router = APIRouter()

throttle = LoginThrottle()


def connection_user(connection: HTTPConnection) -> User | None:
    """Return the user signed in on this request or WebSocket, or None."""
    return auth.user_from_token(connection.cookies.get(SESSION_COOKIE))


def require_user(request: Request) -> User:
    """Dependency: the signed-in user; 401 when nobody is."""
    user = connection_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to use Sibyl")
    return user


def require_admin(user: Annotated[User, Depends(require_user)]) -> User:
    """Dependency: the signed-in user, who must be an admin."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only administrators can do this")
    return user


SignedIn = Annotated[User, Depends(require_user)]
Admin = Annotated[User, Depends(require_admin)]


def describe(user: User) -> CurrentUser:
    """Describe ``user`` for the web app."""
    return CurrentUser(username=user.username, is_admin=user.is_admin, auth_enabled=auth.auth_enabled())


@router.post("/auth/login")
async def login(body: LoginRequest, request: Request, response: Response) -> CurrentUser:
    """Sign in with the username and password of a server account in ``SIBYL_AUTH_GROUP``; sets the session cookie."""
    if not auth.auth_enabled():
        return describe(auth.local_user())
    keys = (f"user:{body.username.strip().lower()}", f"ip:{request.client.host if request.client else '?'}")
    wait = throttle.retry_after(*keys)
    if wait > 0:
        raise HTTPException(status_code=429, detail=f"Too many failed sign-ins. Try again in {int(wait // 60) + 1} minutes.")
    user = await to_thread.run_sync(auth.authenticate, body.username, body.password)
    if user is None:
        throttle.failed(*keys)
        raise HTTPException(status_code=401, detail="Wrong username or password, or this account may not use Sibyl")
    throttle.succeeded(*keys)
    response.set_cookie(
        SESSION_COOKIE,
        auth.create_token(user.username),
        max_age=int(auth.session_seconds()),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https" or auth.secure_cookies(),
    )
    return describe(user)


@router.post("/auth/logout")
async def logout(response: Response) -> LoggedOut:
    """Sign out: clear the session cookie."""
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")
    return LoggedOut(message="Signed out")


@router.get("/auth/me")
async def me(user: SignedIn) -> CurrentUser:
    """Return the signed-in user; 401 when nobody is signed in."""
    return describe(user)
