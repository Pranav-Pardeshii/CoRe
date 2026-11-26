from collections.abc import AsyncIterator
from typing import Any

from fastapi import Request
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import Settings


class DatabaseManager:
    """Manages the single async SQLAlchemy engine and session factory for the app process."""

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def init(
        self,
        settings: Settings,
        *,
        url_override: str | URL | None = None,
    ) -> None:
        """Initialize the async engine and session factory without module-import side effects."""
        connect_args: dict[str, Any] = {}
        if url_override is None:
            connect_args["connect_timeout"] = settings.DB_CONNECT_TIMEOUT
            if settings.DB_UNIX_SOCKET and settings.DB_UNIX_SOCKET.strip():
                connect_args["unix_socket"] = settings.DB_UNIX_SOCKET.strip()
            ssl_context = settings.build_ssl_context()
            if ssl_context is not None:
                connect_args["ssl"] = ssl_context

        target_url = url_override if url_override is not None else settings.async_database_url
        self._engine = create_async_engine(
            target_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_pre_ping=True,
            pool_recycle=settings.DB_POOL_RECYCLE,
            connect_args=connect_args,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("DatabaseManager has not been initialized.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("DatabaseManager has not been initialized.")
        return self._session_factory

    async def dispose(self) -> None:
        """Dispose the engine connection pool during application shutdown."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield one AsyncSession per HTTP request from application state."""
    db_manager: DatabaseManager = request.app.state.db_manager
    async with db_manager.session_factory() as session:
        yield session
