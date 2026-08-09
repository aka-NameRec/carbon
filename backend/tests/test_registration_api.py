"""Integration tests for the producer registration vertical slice."""

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


@pytest.mark.integration
async def test_registration_creates_one_projection_and_one_vault_file(tmp_path: Path) -> None:
    """A duplicate producer key returns the original resource without another file."""

    raw_token = "test-producer-token"
    token_file = tmp_path / "tokens.json"
    token_file.write_text(
        json.dumps([{"hash": hashlib.sha256(raw_token.encode()).hexdigest(), "scope": "producer"}]),
        encoding="utf-8",
    )
    os.chmod(token_file, 0o600)
    vault_root = tmp_path / "Notifications"
    settings = Settings(vault_root=vault_root, token_file=token_file)
    app = create_app(settings)
    deduplication_key = f"test-{uuid4().hex}"
    payload = {
        "source": "test-source",
        "title": "Registration test",
        "occurred_at": "2026-08-09T07:42:18Z",
        "body": "A **Markdown** body.",
        "deduplication_key": deduplication_key,
        "tags": ["test"],
    }

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(
                "/api/v1/messages", json=payload, headers={"Authorization": f"Bearer {raw_token}"}
            )
            replay = await client.post(
                "/api/v1/messages", json=payload, headers={"Authorization": f"Bearer {raw_token}"}
            )

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.headers["X-Idempotent-Replay"] == "true"
    assert replay.json() == first.json()
    public_id = first.json()["public_id"]
    assert list(vault_root.rglob(f"{public_id}.md"))

    engine = create_database_engine(settings.database_dsn)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM messages WHERE public_id = :public_id"), {"public_id": public_id}
            )
    finally:
        await engine.dispose()
