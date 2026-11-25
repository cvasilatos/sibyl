"""Request and response models for signing in."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """A username and password for the server's own accounts."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class CurrentUser(BaseModel):
    """The signed-in user."""

    username: str
    is_admin: bool
    """Admins may delete or cancel anyone's reviews, delete any saved form and delete models."""
    auth_enabled: bool
    """False when sign-in is off (``SIBYL_AUTH=none``): everyone is the admin user ``local``."""


class LoggedOut(BaseModel):
    """Confirmation of signing out."""

    message: str
