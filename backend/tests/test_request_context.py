"""Request correlation and safe access logging tests."""

import json
import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.request_context import RequestContextMiddleware
from app.main import app


@pytest.mark.asyncio
async def test_request_id_is_returned_and_preserved(caplog):
    caplog.set_level(logging.INFO, logger="recipelity.access")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/health/live?token=must-not-be-logged",
            headers={"X-Request-ID": "idea-check-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "idea-check-123"
    event = json.loads(caplog.records[-1].message)
    assert event["request_id"] == "idea-check-123"
    assert event["path"] == "/health/live"
    assert "must-not-be-logged" not in caplog.text


@pytest.mark.asyncio
async def test_invalid_request_id_is_replaced():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/health/live",
            headers={"X-Request-ID": "invalid request id\nvalue"},
        )

    request_id = response.headers["X-Request-ID"]
    assert request_id != "invalid request id\nvalue"
    assert len(request_id) == 32


@pytest.mark.asyncio
async def test_unhandled_error_returns_safe_response_with_request_id(caplog):
    test_app = FastAPI()
    test_app.add_middleware(RequestContextMiddleware)

    @test_app.get("/fail")
    async def fail():
        raise RuntimeError("DATABASE_URL=mysql://user:secret@example/db")

    caplog.set_level(logging.ERROR, logger="recipelity.access")
    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/fail")

    assert response.status_code == 500
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert response.json()["detail"] == "服务器内部错误，请稍后重试"
    assert "secret" not in caplog.text
    assert json.loads(caplog.records[-1].message)["error_type"] == "RuntimeError"
