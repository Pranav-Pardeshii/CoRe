import re

from pydantic import BaseModel, Field, field_validator

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")


class UserRegisterRequest(BaseModel):
    """Request payload for user registration."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """Strip whitespace and enforce strict username character rules."""
        cleaned = value.strip()
        if not _USERNAME_RE.match(cleaned):
            raise ValueError("Username must be 3-50 chars using letters, digits, '.', '_', or '-'.")
        return cleaned


class RegisterResponse(BaseModel):
    """Response payload after successful registration."""

    message: str


class TokenResponse(BaseModel):
    """OAuth2 bearer token response."""

    access_token: str
    token_type: str = "bearer"
