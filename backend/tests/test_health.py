"""Health endpoint tests."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from carbon_backend.config import Settings
from carbon_backend.main import create_app


@pytest.mark.asyncio
async def test_liveness_does_not_require_dependencies() -> None:
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_readiness_reports_unavailable_vault(tmp_path: Path) -> None:
    settings = Settings(vault_root=tmp_path / "missing")
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "storage_error"
