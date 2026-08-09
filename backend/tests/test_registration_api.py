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
from carbon_backend.repositories.messages import MessageRepository
from carbon_backend.services.rebuild import rebuild_projection


@pytest.mark.integration
async def test_registration_creates_one_projection_and_one_vault_file(tmp_path: Path) -> None:
    """A duplicate producer key returns the original resource without another file."""

    raw_token = "test-producer-token"
    viewer_token = "test-viewer-token"
    token_file = tmp_path / "tokens.json"
    token_file.write_text(
        json.dumps(
            [
                {"hash": hashlib.sha256(raw_token.encode()).hexdigest(), "scope": "producer"},
                {"hash": hashlib.sha256(viewer_token.encode()).hexdigest(), "scope": "viewer"},
            ]
        ),
        encoding="utf-8",
    )
    os.chmod(token_file, 0o600)
    vault_root = tmp_path / "Notifications"
    settings = Settings(vault_root=vault_root, token_file=token_file)
    app = create_app(settings)
    deduplication_key = f"test-{uuid4().hex}"
    payload = {
        "source": "test-source",
        "title": f"Registration test {deduplication_key}",
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
            russian_deduplication_key = f"test-{uuid4().hex}"
            russian = await client.post(
                "/api/v1/messages",
                json={
                    **payload,
                    "source": "tg-mon",
                    "title": f"Новое уведомление {russian_deduplication_key}",
                    "deduplication_key": russian_deduplication_key,
                },
                headers={"Authorization": f"Bearer {raw_token}"},
            )
            public_id = first.json()["public_id"]
            viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
            listed = await client.get("/api/v1/messages", headers=viewer_headers)
            search = await client.get(
                "/api/v1/messages/search", params={"q": "Registration"}, headers=viewer_headers
            )
            russian_search = await client.get(
                "/api/v1/messages/search", params={"q": "уведомления"}, headers=viewer_headers
            )
            trigram_search = await client.get(
                "/api/v1/messages/search", params={"q": "tg-mo"}, headers=viewer_headers
            )
            marked_read = await client.post(
                f"/api/v1/messages/{public_id}/read", headers=viewer_headers
            )
            detail = await client.get(f"/api/v1/messages/{public_id}", headers=viewer_headers)
            deleted = await client.delete(f"/api/v1/messages/{public_id}", headers=viewer_headers)
            listed_after_delete = await client.get("/api/v1/messages", headers=viewer_headers)

    assert first.status_code == 201
    assert replay.status_code == 200
    assert russian.status_code == 201
    assert replay.headers["X-Idempotent-Replay"] == "true"
    assert replay.json() == first.json()
    assert listed.status_code == 200
    assert search.status_code == 200
    assert search.json()["items"][0]["public_id"] == public_id
    assert russian_search.json()["items"][0]["source"] == "tg-mon"
    assert trigram_search.json()["items"][0]["source"] == "tg-mon"
    assert marked_read.status_code == 204
    assert detail.json()["read_at"] is not None
    assert deleted.status_code == 204
    assert public_id not in {item["public_id"] for item in listed_after_delete.json()["items"]}
    assert list((vault_root / ".trash").rglob(f"{public_id}.md"))

    engine = create_database_engine(settings.database_dsn)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DELETE FROM messages WHERE source = 'test-source'"))
        report = await rebuild_projection(MessageRepository(engine), vault_root, dry_run=False)
        assert report.added == 1
        async with engine.connect() as connection:
            restored = await connection.execute(
                text("SELECT deleted_at FROM messages WHERE public_id = :public_id"),
                {"public_id": public_id},
            )
            assert restored.scalar_one() is not None
        async with engine.begin() as connection:
            await connection.execute(text("DELETE FROM messages WHERE source = 'test-source'"))
    finally:
        await engine.dispose()
