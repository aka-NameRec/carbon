"""Safe vault scanning for rebuilding the PostgreSQL projection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML

from carbon_backend.storage.vault import PUBLIC_ID_PATTERN

if TYPE_CHECKING:
    from carbon_backend.repositories.messages import MessageRepository


@dataclass(slots=True)
class RebuildReport:
    """Non-destructive scan result suitable for dry-run output."""

    added: int = 0
    updated: int = 0
    removed: int = 0
    skipped: int = 0
    failed: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class VaultRecord:
    """Validated vault content ready for a PostgreSQL projection upsert."""

    data: dict[str, object]
    body_markdown: str
    relative_path: Path
    deleted: bool


def scan_vault(root: Path) -> RebuildReport:
    """Validate active/trash Markdown files without changing vault or PostgreSQL."""

    report = RebuildReport()
    seen: set[str] = set()
    for path in root.rglob("*.md"):
        if path.name.startswith(".carbon-tmp-"):
            report.skipped += 1
            continue
        try:
            public_id = _validate_file(path)
        except ValueError as error:
            report.failed.append(f"{path.relative_to(root)}: {error}")
            continue
        if public_id in seen:
            report.failed.append(f"{path.relative_to(root)}: duplicate public_id {public_id}")
            continue
        seen.add(public_id)
        report.added += 1
    return report


def load_records(root: Path, report: RebuildReport) -> list[VaultRecord]:
    """Return valid active/trash records while adding diagnostics to ``report``."""

    records: list[VaultRecord] = []
    seen: set[str] = set()
    for path in root.rglob("*.md"):
        if path.name.startswith(".carbon-tmp-"):
            report.skipped += 1
            continue
        try:
            data, body = _load_file(path)
            public_id = _validate_data(data)
        except ValueError as error:
            report.failed.append(f"{path.relative_to(root)}: {error}")
            continue
        if public_id in seen:
            report.failed.append(f"{path.relative_to(root)}: duplicate public_id {public_id}")
            continue
        seen.add(public_id)
        records.append(
            VaultRecord(data, body, path.relative_to(root), path.is_relative_to(root / ".trash"))
        )
    return records


def collect_present_ids(root: Path) -> set[str]:
    """Return public_ids of all non-temporary Markdown files (active and trash).

    Presence is derived from the file name so that a corrupted-but-existing
    canonical file still counts as present and never triggers a prune.
    """

    present: set[str] = set()
    for path in root.rglob("*.md"):
        if path.name.startswith(".carbon-tmp-"):
            continue
        if PUBLIC_ID_PATTERN.fullmatch(path.stem):
            present.add(path.stem)
    return present


async def rebuild_projection(
    repository: MessageRepository, root: Path, dry_run: bool
) -> RebuildReport:
    """Scan vault, upsert valid records, and prune projection rows without a file."""

    report = RebuildReport()
    records = load_records(root, report)
    present_ids = collect_present_ids(root)
    orphan_ids = set(await repository.list_public_ids()) - present_ids
    if dry_run:
        report.added = len(records)
        report.removed = len(orphan_ids)
        return report
    for record in records:
        if await repository.upsert_rebuild_record(record):
            report.added += 1
        else:
            report.updated += 1
    if orphan_ids:
        report.removed = await repository.delete_public_ids(sorted(orphan_ids))
    return report


def _validate_file(path: Path) -> str:
    data, _ = _load_file(path)
    return _validate_data(data)


def _load_file(path: Path) -> tuple[dict[str, object], str]:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValueError("missing frontmatter")
    _, frontmatter, body = content.split("---\n", 2)
    data = YAML(typ="safe").load(frontmatter)
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data, body.lstrip("\n").rstrip("\n")


def _validate_data(data: dict[str, object]) -> str:
    required = {
        "schema_version",
        "public_id",
        "source",
        "title",
        "occurred_at",
        "received_at",
        "content_hash",
    }
    if missing := required.difference(data):
        raise ValueError(f"missing fields: {', '.join(sorted(missing))}")
    if data["schema_version"] != 1:
        raise ValueError("unsupported schema_version")
    public_id = data["public_id"]
    if not isinstance(public_id, str) or not PUBLIC_ID_PATTERN.fullmatch(public_id):
        raise ValueError("invalid public_id")
    return public_id
