"""CORS origin-allowlist tests for the local-only API.

After removing token auth, CORS origin checking is the drive-by / DNS-rebinding
defense, so these tests pin the allowlist behavior and guard against an accidental
regression to ``allow_origins=["*"]``.
"""

from __future__ import annotations

import httpx
import pytest

from carbon_backend.config import DEFAULT_CORS_ORIGINS, Settings
from carbon_backend.main import create_app

ALLOWED_ORIGIN = DEFAULT_CORS_ORIGINS[0]
DISALLOWED_ORIGIN = "https://evil.example"


@pytest.mark.asyncio
async def test_preflight_allows_webview_origin() -> None:
    app = create_app(Settings(cors_origins=DEFAULT_CORS_ORIGINS))
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/messages",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


@pytest.mark.asyncio
async def test_preflight_rejects_disallowed_origin() -> None:
    app = create_app(Settings(cors_origins=DEFAULT_CORS_ORIGINS))
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/messages",
            headers={
                "Origin": DISALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    # No allow-origin header reaches the browser, so the drive-by request is blocked
    # regardless of whether starlette returns 400 or 200 here.
    assert "access-control-allow-origin" not in response.headers
