"""Producer input normalization and stable message identity."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field, field_validator

SOURCE_PATTERN = re.compile(r"^[a-z0-9-]{1,32}$")
HTML_TAG_PATTERN = re.compile(r"</?[A-Za-z][^>]*>")
BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
SEVERITY_LEVELS = ("highest", "high", "medium", "low")
SEVERITY_DEFAULT = "medium"


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _base36(value: int) -> str:
    if value == 0:
        return "0"
    chars: list[str] = []
    while value:
        value, remainder = divmod(value, 36)
        chars.append(BASE36_ALPHABET[remainder])
    return "".join(reversed(chars))


class ProducerMessage(BaseModel):
    """Validated producer payload before storage-specific fields are assigned."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: str
    title: str = Field(min_length=1, max_length=500)
    occurred_at: datetime
    body: str = Field(min_length=1, max_length=100_000)
    source_event_id: str | None = Field(default=None, max_length=500)
    deduplication_key: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=32)
    severity: str = Field(default=SEVERITY_DEFAULT)

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, value: str) -> str:
        if value not in SEVERITY_LEVELS:
            raise ValueError(
                f"severity must be one of {', '.join(SEVERITY_LEVELS)}"
            )
        return value

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        normalized = value.lower()
        if not SOURCE_PATTERN.fullmatch(normalized):
            raise ValueError("source must match [a-z0-9-] and be 1 to 32 characters long")
        return normalized

    @field_validator("occurred_at")
    @classmethod
    def normalize_occurred_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("body")
    @classmethod
    def reject_raw_html(cls, value: str) -> str:
        if HTML_TAG_PATTERN.search(value):
            raise ValueError("body must not contain raw HTML")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized = sorted({tag.strip().lower() for tag in value})
        if any(not tag or len(tag) > 64 for tag in normalized):
            raise ValueError("tags must be non-empty and at most 64 characters long")
        return normalized


def canonical_payload(message: ProducerMessage) -> bytes:
    """Return the stable byte representation used by hashing and public IDs."""

    payload = {
        "body": message.body,
        "occurred_at": _utc_iso(message.occurred_at),
        "source": message.source,
        "source_event_id": message.source_event_id,
        "title": message.title,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def content_hash(message: ProducerMessage) -> str:
    """Return the SHA-256 hash of canonical producer content."""

    return hashlib.sha256(canonical_payload(message)).hexdigest()


def public_id(message: ProducerMessage, *, nonce: int = 0) -> str:
    """Build a stable external ID; callers retry with a deterministic nonce on collision."""

    timestamp = _base36(int(message.occurred_at.timestamp()))
    digest = hashlib.sha256(canonical_payload(message) + f":{nonce}".encode()).digest()
    suffix = _base36(int.from_bytes(digest[:8], "big") % (36**8)).rjust(8, "0")
    return f"{timestamp}-{message.source}-{suffix}"


def markdown_to_plain_text(markdown: str) -> str:
    """Extract visible Markdown text without parsing or executing HTML."""

    parser = MarkdownIt("commonmark", {"html": False})
    fragments: list[str] = []
    for token in parser.parse(markdown):
        if token.type in {"fence", "code_block"}:
            fragments.append(token.content)
        if token.type != "inline" or token.children is None:
            continue
        inline_fragments: list[str] = []
        for child in token.children:
            if child.type in {"text", "code_inline", "html_inline"}:
                inline_fragments.append(child.content)
            elif child.type in {"softbreak", "hardbreak"}:
                inline_fragments.append(" ")
        fragments.append("".join(inline_fragments))
    return " ".join(" ".join(fragments).split())
