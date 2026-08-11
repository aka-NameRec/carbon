"""Filesystem-coordinated read state and recoverable deletion workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from carbon_backend.repositories.messages import MessageRepository, PendingMessage
from carbon_backend.storage.vault import VaultMessage, VaultStorage


class LifecycleService:
    """Keep canonical vault files and locked projection rows consistent."""

    def __init__(self, repository: MessageRepository, storage: VaultStorage) -> None:
        self._repository = repository
        self._storage = storage

    async def set_read_state(self, public_id: str, read: bool) -> bool:
        """Synchronize read state to frontmatter and PostgreSQL."""

        pending = await self._repository.lock_active(public_id)
        if pending is None:
            return False
        row = pending.row
        assert row is not None
        read_at = datetime.now(UTC) if read else None
        relative_path = Path(cast(str, row["file_path"]))
        previous: bytes | None = None
        try:
            previous = self._storage.rewrite(relative_path, self._message(pending, read_at, None))
            await self._repository.update_lifecycle(
                pending, read_at=read_at, deleted_at=None, file_path=str(relative_path)
            )
            await pending.commit()
        except Exception:
            if previous is not None:
                self._storage.restore(relative_path, previous)
            await pending.rollback()
            raise
        return True

    async def delete(self, public_id: str) -> bool:
        """Move a message into trash and mark its projection as deleted."""

        pending = await self._repository.lock_active(public_id)
        if pending is None:
            return False
        row = pending.row
        assert row is not None
        deleted_at = datetime.now(UTC)
        read_at = cast(datetime | None, row["read_at"])
        relative_path = Path(cast(str, row["file_path"]))
        previous: bytes | None = None
        trashed = False
        try:
            previous = self._storage.rewrite(
                relative_path, self._message(pending, read_at, deleted_at)
            )
            trash_path = self._storage.move_to_trash(relative_path)
            trashed = True
            await self._repository.update_lifecycle(
                pending,
                read_at=read_at,
                deleted_at=deleted_at,
                file_path=str(trash_path),
            )
            await pending.commit()
        except Exception:
            if trashed:
                self._storage.restore_from_trash(relative_path)
            if previous is not None:
                self._storage.restore(relative_path, previous)
            await pending.rollback()
            raise
        return True

    @staticmethod
    def _message(
        pending: PendingMessage, read_at: object, deleted_at: datetime | None
    ) -> VaultMessage:
        row = pending.row
        assert row is not None
        return VaultMessage(
            public_id=pending.public_id,
            source=cast(str, row["source"]),
            title=cast(str, row["title"]),
            occurred_at=cast(datetime, row["occurred_at"]),
            received_at=pending.received_at,
            body_markdown=cast(str, row["body_markdown"]),
            content_hash=pending.content_hash,
            tags=tuple(cast(list[str], row["tags"])),
            source_event_id=cast(str | None, row["source_event_id"]),
            deduplication_key=cast(str | None, row["deduplication_key"]),
            read_at=cast(datetime | None, read_at),
            deleted_at=deleted_at,
            severity=cast(str, row["severity"]),
            schema_version=cast(int, row["schema_version"]),
        )
