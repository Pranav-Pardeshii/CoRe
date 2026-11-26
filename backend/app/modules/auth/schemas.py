from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    """Request payload for user registration."""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)


class RegisterResponse(BaseModel):
    """Response payload after successful registration."""

    message: str


class TokenResponse(BaseModel):
    """OAuth2 bearer token response."""

    access_token: str
    token_type: str = "bearer"
