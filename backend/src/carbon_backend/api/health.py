"""Liveness and readiness endpoints."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from carbon_backend.errors import ApiError

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """A successful health-check response."""

    status: Literal["ok"]


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Report that the application process can answer HTTP requests."""

    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def readiness(request: Request) -> HealthResponse:
    """Verify required development dependencies without touching application data."""

    settings = request.app.state.settings
    if not settings.vault_root.is_dir() or not os.access(settings.vault_root, os.W_OK):
        raise ApiError(
            status_code=503,
            code="storage_error",
            message="Vault root is unavailable",
        )

    try:
        async with request.app.state.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise ApiError(
            status_code=503,
            code="projection_error",
            message="Database is unavailable",
        ) from error

    return HealthResponse(status="ok")
