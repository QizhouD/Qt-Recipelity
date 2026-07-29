"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai import router as ai_router
from app.api.media import router as media_router
from app.api.recipes import router as recipes_router
from app.core.config import settings
from app.db.session import Base, engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Conditionally auto-create tables on startup.

    Production deploys use Alembic (alembic upgrade head).  Set
    AUTO_CREATE_TABLES=true only for quick local dev without a migration step.
    """
    if settings.auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Recipelity API",
    version="0.1.0",
    description="Intelligent Recipe Management System — REST API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recipes_router)
app.include_router(ai_router)
app.include_router(media_router)

# Mount the uploads directory for static media access
media_dir = Path(settings.media_root)
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_dir), name="media")

# ── Global exception handlers — never leak stack traces ─────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch-all: log the real error, return a safe message to the client."""
    import logging

    logger = logging.getLogger("recipelity")
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


@app.get("/health/live")
async def health_live():
    """Lightweight liveness probe — no DB access."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready(db: AsyncSession = Depends(get_db)):
    """Readiness probe — verifies the database is reachable by executing SELECT 1.

    Returns HTTP 503 with a safe error message when the database is unavailable.
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database not reachable",
        ) from exc
