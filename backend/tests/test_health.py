"""Health-check tests — liveness and readiness."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient):
    """Liveness probe returns 200 without any DB access."""
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_ready_success(client: AsyncClient):
    """Readiness probe returns 200 when DB is reachable."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_health_ready_db_unavailable():
    """Readiness probe returns 503 when the database is unreachable.

    Uses a separate app instance with a broken DB override to avoid
    affecting other tests.
    """
    # Save the original override (set by conftest.py)
    original_override = app.dependency_overrides.get(get_db)

    # Create a broken engine pointing nowhere
    broken_engine = create_async_engine(
        "sqlite+aiosqlite:///dev/null/nonexistent/broken.db", echo=False
    )
    broken_factory = async_sessionmaker(
        broken_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_broken_db():
        async with broken_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_broken_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health/ready")
            assert resp.status_code == 503
            assert "Database not reachable" in resp.json()["detail"]
    finally:
        # Restore the original override
        if original_override is not None:
            app.dependency_overrides[get_db] = original_override
        else:
            app.dependency_overrides.pop(get_db, None)
        await broken_engine.dispose()
