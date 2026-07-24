"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/recipes.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Generative AI (optional; never commit the API key)
    ai_provider: str = "openai"
    openai_api_key: str = ""
    ai_vision_model: str = "gpt-5.6-luna"
    ai_image_model: str = "gpt-image-2"
    ai_request_timeout: int = 90
    generated_media_dir: str = "data/generated"

    # Security
    allowed_origins: str = "http://localhost:5173"

    # Upload limits
    image_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    image_max_pixels: int = 4096 * 4096


settings = Settings()
