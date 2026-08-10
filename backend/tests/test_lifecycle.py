"""Integration tests for filesystem-coordinated lifecycle error paths."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from carbon_backend.config import Settings
from carbon_backend.database import create_database_engine
from carbon_backend.main import create_app


def _token_file(tmp_path: Path, producer_token: str, viewer_token: str) -> Path:
    """Write a local token store with distinct producer and viewer tokens."""

    token_file = tmp_path / "tokens.json"
    token_file.write_text(
        json.dumps(
            [
                {"hash": hashlib.sha256(producer_token.encode()).hexdigest(), "scope": "producer"},
                {"hash": hashlib.sha256(viewer_token.encode()).hexdigest(), "scope": "viewer"},
            ]
        ),
        encoding="utf-8",
    )
    os.chmod(token_file, 0o600)
    return token_file


@pytest.mark.integration
async def test_failed_read_sync_does_not_leak_a_row_lock(tmp_path: Path) -> None:
    """A read-state sync that fails on a missing vault file must roll back its lock.

    With the old code the SELECT ... FOR UPDATE transaction stayed open and blocked
    any later write on the same row; the probe DELETE would hit lock_timeout.
    """

    producer_token = "test-producer-token"
    viewer_token = "test-viewer-token"
    settings = Settings(
        vault_root=tmp_path / "Notifications",
        token_file=_token_file(tmp_path, producer_token, viewer_token),
    )
    app = create_app(settings)
    producer_headers = {"Authorization": f"Bearer {producer_token}"}
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    stamp = uuid4().hex
    payload = {
        "source": "test-source",
        "title": f"Leak test {stamp}",
        "occurred_at": "2026-08-09T07:42:18Z",
        "body": "body",
        "deduplication_key": f"test-{stamp}",
    }

    engine = create_database_engine(settings.database_dsn)
    try:
        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                created = await client.post(
                    "/api/v1/messages", json=payload, headers=producer_headers
                )
                assert created.status_code == 201, created.text
                public_id = created.json()["public_id"]

                canonical = list((tmp_path / "Notifications").rglob(f"{public_id}.md"))
                assert len(canonical) == 1
                canonical[0].unlink()  # the projection row is now an orphan

                failed = await client.post(
                    f"/api/v1/messages/{public_id}/read", headers=viewer_headers
                )
            assert failed.status_code == 500

            # The app engine is still alive here, so a leaked transaction would still hold
            # the row lock and this DELETE would block until lock_timeout.
            async with engine.connect() as connection:
                await connection.execute(text("SET lock_timeout = '2s'"))
                await connection.execute(
                    text("DELETE FROM messages WHERE public_id = :public_id"),
                    {"public_id": public_id},
                )
    finally:
        async with engine.begin() as connection:
            await connection.execute(text("DELETE FROM messages WHERE source = 'test-source'"))
        await engine.dispose()
