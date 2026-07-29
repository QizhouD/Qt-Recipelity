"""Alembic environment configuration — reads DATABASE_URL from app settings.

Supports both sync and async database URLs (asyncmy, aiosqlite, etc.).
"""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings  # noqa: E402  — reads DATABASE_URL env
from app.db.session import Base  # noqa: E402 — DeclarativeBase
from app.models.recipe import (  # noqa: E402, F401 — register all models for autogenerate
    Ingredient,
    Nutrition,
    Recipe,
    Step,
    Tag,
)

# Alembic Config object
config = context.config

# Override sqlalchemy.url from settings (environment-aware)
config.set_main_option("sqlalchemy.url", settings.database_url)

# Setup loggers from the ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Execute migrations with the given connection (sync wrapper for async)."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to the database).

    Uses asyncio.run() to support async database drivers (asyncmy, aiosqlite).
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
