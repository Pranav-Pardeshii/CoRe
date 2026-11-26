from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings
from backend.app.core.exceptions import ConflictError, UnauthorizedError
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.modules.auth.repository import AuthRepository
from backend.app.modules.auth.schemas import RegisterResponse, TokenResponse


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
        hashed_password = hash_password(password)
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
    ) -> TokenResponse:
        user = await self._repository.get_by_username(session, username=username)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid username or password.")

        token = create_access_token(
            {"sub": str(user.id), "username": user.username},
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
            expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )
        return TokenResponse(access_token=token, token_type="bearer")
