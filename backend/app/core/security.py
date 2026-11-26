from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from backend.app.core.config import Settings, get_app_settings

JWT_ISSUER = "core-api"
JWT_AUDIENCE = "core-client"
JWT_TOKEN_TYPE = "access"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
_password_hasher = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = _password_hasher.hash("core-dummy-timing-equalization-password")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored Argon2id hash."""
    return _password_hasher.verify(plain_password, hashed_password)


def verify_dummy_password(plain_password: str) -> bool:
    """Run a constant-work Argon2id verification against a precomputed dummy hash."""
    return _password_hasher.verify(plain_password, _DUMMY_PASSWORD_HASH)


def create_access_token(
    data: dict[str, Any],
    *,
    secret_key: str,
    algorithm: str = "HS256",
    expires_minutes: int = 60,
) -> str:
    """Create a signed JWT with standard claims without mutating the caller's dict."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    to_encode["iat"] = now
    to_encode["exp"] = now + timedelta(minutes=expires_minutes)
    to_encode["iss"] = JWT_ISSUER
    to_encode["aud"] = JWT_AUDIENCE
    to_encode["type"] = JWT_TOKEN_TYPE
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def decode_access_token(
    token: str,
    *,
    secret_key: str,
    algorithm: str = "HS256",
) -> dict[str, Any]:
    """Decode and validate a JWT signature, expiration, issuer, audience, and type."""
    payload = jwt.decode(
        token,
        secret_key,
        algorithms=[algorithm],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={"require": ["exp", "iat", "iss", "aud", "type"]},
    )
    if payload.get("type") != JWT_TOKEN_TYPE:
        raise jwt.InvalidTokenError("Invalid token type.")
    return payload


def get_current_user_id(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_app_settings),
) -> int:
    """Extract and validate the authenticated user's integer ID from the Bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(
            token,
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
