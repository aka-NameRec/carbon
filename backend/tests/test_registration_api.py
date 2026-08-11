"""Integration tests for the producer registration vertical slice."""

from __future__ import annotations

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

    vault_root = tmp_path / "Notifications"
    settings = Settings(vault_root=vault_root)
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
            first = await client.post("/api/v1/messages", json=payload)
            replay = await client.post("/api/v1/messages", json=payload)
            russian_deduplication_key = f"test-{uuid4().hex}"
            russian = await client.post(
                "/api/v1/messages",
                json={
                    **payload,
                    "source": "tg-mon",
                    "title": f"Новое уведомление {russian_deduplication_key}",
                    "deduplication_key": russian_deduplication_key,
                },
            )
            public_id = first.json()["public_id"]
            russian_public_id = russian.json()["public_id"]
            listed = await client.get("/api/v1/messages")
            search = await client.get("/api/v1/messages/search", params={"q": "Registration"})
            russian_search = await client.get(
                "/api/v1/messages/search", params={"q": "уведомления"}
            )
            trigram_search = await client.get(
                "/api/v1/messages/search", params={"q": "tg-mo"}
            )
            marked_read = await client.post(f"/api/v1/messages/{public_id}/read")
            detail = await client.get(f"/api/v1/messages/{public_id}")
            deleted = await client.delete(f"/api/v1/messages/{public_id}")
            listed_after_delete = await client.get("/api/v1/messages")

    engine = create_database_engine(settings.database_dsn)
    try:
        assert first.status_code == 201
        assert replay.status_code == 200
        assert russian.status_code == 201
        assert replay.headers["X-Idempotent-Replay"] == "true"
        assert replay.json() == first.json()
        assert listed.status_code == 200
        # Default severity is medium, so no message counts as important.
        assert listed.json()["unread_important_count"] == 0
        assert search.status_code == 200
        assert search.json()["items"][0]["public_id"] == public_id
        assert russian_search.json()["items"][0]["source"] == "tg-mon"
        assert trigram_search.json()["items"][0]["source"] == "tg-mon"
        assert marked_read.status_code == 204
        assert detail.json()["read_at"] is not None
        assert deleted.status_code == 204
        assert public_id not in {item["public_id"] for item in listed_after_delete.json()["items"]}
        assert list((vault_root / ".trash").rglob(f"{public_id}.md"))

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
    finally:
        # Remove exactly the rows this test created (tg-mon is a real source, so delete
        # by public_id, not by source) and run even if an assertion above failed.
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM messages WHERE public_id IN (:test_id, :russian_id)"),
                {"test_id": public_id, "russian_id": russian_public_id},
            )
        await engine.dispose()


@pytest.mark.integration
async def test_high_severity_drives_important_unread_indicator(tmp_path: Path) -> None:
    """An unread high-severity message is reflected in unread_important_count."""

    vault_root = tmp_path / "Notifications"
    settings = Settings(vault_root=vault_root)
    app = create_app(settings)
    stamp = uuid4().hex
    payload = {
        "source": "test-source",
        "title": f"Important {stamp}",
        "occurred_at": "2026-08-09T07:42:18Z",
        "body": "body",
        "deduplication_key": f"high-{stamp}",
        "severity": "high",
    }

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post("/api/v1/messages", json=payload)
            public_id = created.json()["public_id"]
            listed = await client.get("/api/v1/messages")
            detail = await client.get(f"/api/v1/messages/{public_id}")

    engine = create_database_engine(settings.database_dsn)
    try:
        assert created.status_code == 201
        listed_body = listed.json()
        assert listed_body["unread_count"] == 1
        assert listed_body["unread_important_count"] == 1
        assert listed_body["items"][0]["severity"] == "high"
        assert detail.json()["severity"] == "high"
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM messages WHERE public_id = :public_id"),
                {"public_id": public_id},
            )
        await engine.dispose()
