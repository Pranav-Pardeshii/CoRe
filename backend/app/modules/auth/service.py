import asyncio

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings
from backend.app.core.exceptions import ConflictError, UnauthorizedError
from backend.app.core.rate_limit import InMemoryRateLimiter
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_dummy_password,
    verify_password,
)
from backend.app.modules.auth.repository import AuthRepository
from backend.app.modules.auth.schemas import RegisterResponse, TokenResponse

_MAX_LOGIN_PASSWORD_LENGTH = 128


class AuthService:
    """Business logic for user registration and JWT authentication."""

    def __init__(self, repository: AuthRepository | None = None) -> None:
        self._repository = repository or AuthRepository()

    async def register(
        self,
        session: AsyncSession,
        *,
        username: str,
        password: str,
    ) -> RegisterResponse:
        hashed_password = await asyncio.to_thread(hash_password, password)
        try:
            await self._repository.create_user(
                session,
                username=username,
                hashed_password=hashed_password,
            )
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise ConflictError("Username already exists.") from exc
        return RegisterResponse(message="User registered successfully.")

    async def login(
        self,
        session: AsyncSession,
        *,
        username: str,
        password: str,
        settings: Settings,
        limiter: InMemoryRateLimiter | None = None,
    ) -> TokenResponse:
        normalized_username = username.strip()
        throttle_key = f"login_user:{normalized_username}"

        if limiter is not None and not limiter.is_allowed(
            throttle_key,
            max_requests=settings.AUTH_LOGIN_USERNAME_MAX_ATTEMPTS,
            window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts for this account. Please try again later.",
            )

        if not password or len(password) > _MAX_LOGIN_PASSWORD_LENGTH:
            if limiter is not None:
                limiter.record(
                    throttle_key,
                    window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
                )
            raise UnauthorizedError("Invalid username or password.")

        user = await self._repository.get_by_username(session, username=normalized_username)
        if user is None:
            await asyncio.to_thread(verify_dummy_password, password)
            if limiter is not None:
                limiter.record(
                    throttle_key,
                    window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
                )
            raise UnauthorizedError("Invalid username or password.")

        is_valid = await asyncio.to_thread(verify_password, password, user.password_hash)
        if not is_valid:
            if limiter is not None:
                limiter.record(
                    throttle_key,
                    window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
                )
            raise UnauthorizedError("Invalid username or password.")

        if limiter is not None:
            limiter.clear(throttle_key)

        token = create_access_token(
            {"sub": str(user.id), "username": user.username},
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
            expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )
        return TokenResponse(access_token=token, token_type="bearer")
