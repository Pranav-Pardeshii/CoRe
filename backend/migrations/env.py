import asyncio
from logging.config import fileConfig
from typing import Any

from alembic import context
from backend.app.core.config import get_settings
from backend.app.infrastructure.database.model_registry import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url_and_connect_args() -> tuple[str, dict[str, Any]]:
    """Resolve database URL from Alembic config override or application settings."""
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return configured_url, {}

    settings = get_settings()
    connect_args: dict[str, Any] = {}
    ssl_context = settings.build_ssl_context()
    if ssl_context is not None:
        connect_args["ssl"] = ssl_context
    return settings.async_database_url.render_as_string(hide_password=False), connect_args


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode without a live database connection."""
    url = config.get_main_option("sqlalchemy.url") or "mysql+asyncmy://user:pass@localhost/core"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using an async SQLAlchemy engine."""
    url, connect_args = _get_url_and_connect_args()
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entrypoint for online Alembic migrations."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
