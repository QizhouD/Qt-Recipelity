"""AI endpoint validation and safe-degradation tests."""

from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.core.config import settings
from app.main import app


def valid_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color="tomato").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_recipe_from_image_rejects_non_image():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ai/recipe-from-image",
            files={"file": ("recipe.txt", b"not an image", "text/plain")},
        )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_recipe_from_image_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ai/recipe-from-image",
            files={"file": ("food.png", valid_png(), "image/png")},
        )
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


@pytest.mark.asyncio
async def test_image_generation_validates_recipe_text():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ai/image-from-recipe",
            json={"recipe_name": "沙拉", "recipe_text": "太短"},
        )
    assert response.status_code == 422
