"""Database engine and session management — request-scoped via FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_connect_args: dict = {}
_engine_kwargs: dict = {"echo": settings.debug}

if "sqlite" in settings.database_url:
    _connect_args["check_same_thread"] = False
else:
    # MySQL — connection pool settings
    _engine_kwargs.update(
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
    )

engine = create_async_engine(
    settings.database_url,
    **_engine_kwargs,
    connect_args=_connect_args,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
