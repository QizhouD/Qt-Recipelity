"""Recipe image upload tests."""

import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app


@pytest.mark.asyncio
async def test_upload_recipe_image():
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "orange").save(buffer, "PNG")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/media/images",
            files={"file": ("food.png", buffer.getvalue(), "image/png")},
        )
    assert response.status_code == 200
    assert response.json()["image_url"].startswith("/media/recipe-")


@pytest.mark.asyncio
async def test_upload_rejects_text():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/media/images",
            files={"file": ("bad.txt", b"bad", "text/plain")},
        )
    assert response.status_code == 415
