from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.auth.models import User


class AuthRepository:
    """Persistence operations for user accounts."""

    async def get_by_username(self, session: AsyncSession, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, session: AsyncSession, username: str, hashed_password: str) -> User:
        user = User(username=username, password_hash=hashed_password)
        session.add(user)
        await session.flush()
        return user
