"""Deterministic frontmatter rendering and atomic vault writes."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ruamel.yaml import YAML

PUBLIC_ID_PATTERN = re.compile(r"^[a-z0-9]+-[a-z0-9-]+-[a-z0-9]{8}$")


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class VaultMessage:
    """Canonical fields required to serialize one Markdown notification."""

    public_id: str
    source: str
    title: str
    occurred_at: datetime
    received_at: datetime
    body_markdown: str
    content_hash: str
    tags: tuple[str, ...] = ()
    source_event_id: str | None = None
    deduplication_key: str | None = None
    read_at: datetime | None = None
    deleted_at: datetime | None = None
    schema_version: int = 1


def render_markdown(message: VaultMessage) -> str:
    """Render canonical YAML frontmatter and the original Markdown body."""

    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    document = {
        "schema_version": message.schema_version,
        "public_id": message.public_id,
        "source": message.source,
        "title": message.title,
        "occurred_at": _utc_iso(message.occurred_at),
        "received_at": _utc_iso(message.received_at),
        "read_at": _utc_iso(message.read_at),
        "deleted_at": _utc_iso(message.deleted_at),
        "source_event_id": message.source_event_id,
        "deduplication_key": message.deduplication_key,
        "tags": list(message.tags),
        "content_hash": message.content_hash,
    }
    from io import StringIO

    stream = StringIO()
    yaml.dump(document, stream)
    return f"---\n{stream.getvalue()}---\n\n{message.body_markdown}\n"


class VaultStorage:
    """Own atomic writes of active notification files below one vault root."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        """Return the configured notifications root."""

        return self._root

    def relative_path(self, message: VaultMessage) -> Path:
        """Return the verified active relative path for a message."""

        if not PUBLIC_ID_PATTERN.fullmatch(message.public_id):
            raise ValueError("public_id has an invalid file-safe format")
        received_at = message.received_at.astimezone(UTC)
        return Path(f"{received_at:%Y}") / f"{received_at:%m}" / f"{message.public_id}.md"

    def write(self, message: VaultMessage) -> Path:
        """Write one complete file atomically and return its relative vault path."""

        relative_path = self.relative_path(message)
        target = self._root / relative_path
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload = render_markdown(message).encode("utf-8")
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".carbon-tmp-", suffix=".tmp", dir=target.parent, delete=False
            ) as temp_file:
                temp_path = Path(temp_file.name)
                os.chmod(temp_path, 0o600)
                temp_file.write(payload)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, target)
            os.chmod(target, 0o600)
            self._sync_directory(target.parent)
        except OSError as error:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise OSError(
                f"unable to atomically write Carbon vault file {relative_path}"
            ) from error
        return relative_path

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
