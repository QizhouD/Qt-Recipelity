"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Search for .env in the current directory and the parent (repo root)
_ENV_FILE = ".env"
if not Path(_ENV_FILE).exists():
    _PARENT_ENV = Path("..") / _ENV_FILE
    if _PARENT_ENV.exists():
        _ENV_FILE = str(_PARENT_ENV)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database — default to MySQL 8.4; use DATABASE_URL=sqlite+aiosqlite:///... for local dev
    database_url: str = (
        "mysql+asyncmy://recipelity:password@localhost:3306/recipelity?charset=utf8mb4"
    )

    # Dev convenience: set to True to auto-create tables on startup (production uses Alembic)
    auto_create_tables: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    # Generative AI (optional; never commit the API key)
    ai_provider: str = "openai"
    openai_api_key: str = ""
    ai_vision_model: str = "gpt-5.6-luna"
    ai_image_model: str = "gpt-image-2"
    ai_request_timeout: int = 90
    # Security
    allowed_origins: str = "http://localhost:5173"

    # Media storage
    media_root: str = "data/uploads"
    generated_media_dir: str = "data/generated"  # legacy alias; prefer media_root

    # Upload limits
    image_max_bytes: int = 5 * 1024 * 1024  # 5 MB
    image_max_pixels: int = 4096 * 4096


settings = Settings()
