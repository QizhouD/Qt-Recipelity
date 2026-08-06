"""HTTP request correlation and safe structured access logging."""

from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("recipelity.access")


def _request_id(value: str | None) -> str:
    """Return a safe caller-provided request ID or generate a new one."""
    if value and _REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


def _log_event(
    *, request: Request, request_id: str, status_code: int, duration_ms: float,
    error_type: str | None = None,
) -> None:
    """Log an allowlisted JSON event without headers, query strings, or bodies."""
    event: dict[str, object] = {
        "event": "http_request",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
    }
    if error_type:
        event["error_type"] = error_type
    logger.log(
        logging.ERROR if status_code >= 500 else logging.INFO,
        json.dumps(event, ensure_ascii=False, separators=(",", ":")),
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request IDs, safe access logs, and a sanitized 500 response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = _request_id(request.headers.get(REQUEST_ID_HEADER))
        token = request_id_context.set(request_id)
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (perf_counter() - started_at) * 1000
            _log_event(
                request=request,
                request_id=request_id,
                status_code=500,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
            )
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": "服务器内部错误，请稍后重试",
                    "request_id": request_id,
                },
            )
        else:
            _log_event(
                request=request,
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=(perf_counter() - started_at) * 1000,
            )
        finally:
            request_id_context.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
