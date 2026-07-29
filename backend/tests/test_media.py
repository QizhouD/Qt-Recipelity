"""Recipe image upload tests — validation, sizing, and format checks."""

import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app


def _make_png(w: int = 40, h: int = 30) -> bytes:
    """Create a valid PNG image."""
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "orange").save(buf, "PNG")
    return buf.getvalue()


def _make_webp(w: int = 40, h: int = 30) -> bytes:
    """Create a valid WebP image."""
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "blue").save(buf, "WEBP")
    return buf.getvalue()


def _make_jpeg(w: int = 40, h: int = 30) -> bytes:
    """Create a valid JPEG image."""
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "green").save(buf, "JPEG")
    return buf.getvalue()


async def _upload(client: AsyncClient, content: bytes, name: str, content_type: str):
    return await client.post(
        "/api/v1/media/images",
        files={"file": (name, content, content_type)},
    )


@pytest.mark.asyncio
async def test_upload_png_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _upload(client, _make_png(), "food.png", "image/png")
        assert resp.status_code == 200
        data = resp.json()
        assert data["image_url"].startswith("/media/recipe-")
        assert data["image_url"].endswith(".webp")
        image_response = await client.get(data["image_url"])
        assert image_response.status_code == 200
        assert image_response.headers["content-type"] == "image/webp"


@pytest.mark.asyncio
async def test_upload_webp_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _upload(client, _make_webp(), "food.webp", "image/webp")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_upload_jpeg_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _upload(client, _make_jpeg(), "food.jpg", "image/jpeg")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_upload_rejects_text_content_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _upload(client, b"bad", "bad.txt", "text/plain")
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_wrong_extension():
    """Reject .txt file even with valid content-type (mismatched extension)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _upload(client, _make_png(), "bad.txt", "image/png")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_mismatched_image_content_type():
    """A JPEG must not be accepted when declared and named as a PNG."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _upload(client, _make_jpeg(), "dish.png", "image/png")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_corrupt_content():
    """Reject garbage bytes claimed as PNG."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _upload(client, b"\x00\x01\x02" * 10, "corrupt.png", "image/png")
    assert resp.status_code in (400, 415)


@pytest.mark.asyncio
async def test_upload_rejects_huge_file():
    """Reject file larger than 5 MB."""
    transport = ASGITransport(app=app)
    # Create > 5 MB of data (not a valid image, but rejected by size check first)
    huge = b"x" * (6 * 1024 * 1024)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _upload(client, huge, "big.png", "image/png")
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_upload_empty_file():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await _upload(client, b"", "empty.png", "image/png")
    assert resp.status_code == 400
