"""HTTP error types and response envelope helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """A safe API error that follows the Carbon error-envelope contract."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = dict(details or {})


async def api_error_handler(request: Request, error: Exception) -> JSONResponse:
    """Render an ApiError without exposing internal implementation details."""

    api_error = cast(ApiError, error)
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=api_error.status_code,
        content={
            "error": {
                "code": api_error.code,
                "message": api_error.message,
                "details": api_error.details,
                "request_id": request_id,
            }
        },
    )
