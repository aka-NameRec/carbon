"""Hashed local API tokens and scope checks."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from pathlib import Path

from carbon_backend.errors import ApiError


@dataclass(frozen=True, slots=True)
class TokenPrincipal:
    """Authenticated local token identity."""

    scope: str
    source: str | None


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def authenticate(token_file: Path, raw_token: str, required_scope: str) -> TokenPrincipal:
    """Authenticate one bearer token against the owner-only local token file."""

    try:
        entries = json.loads(token_file.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ApiError(
            status_code=401, code="authentication_required", message="Authentication required"
        ) from error
    except json.JSONDecodeError as error:
        raise ApiError(
            status_code=500, code="internal_error", message="Token store is invalid"
        ) from error
    for entry in entries:
        if secrets.compare_digest(entry["hash"], _hash(raw_token)):
            principal = TokenPrincipal(scope=entry["scope"], source=entry.get("source"))
            if principal.scope != required_scope:
                raise ApiError(
                    status_code=403, code="forbidden", message="Required scope is missing"
                )
            return principal
    raise ApiError(
        status_code=401, code="authentication_required", message="Authentication required"
    )


def create_token(token_file: Path, scope: str, source: str | None = None) -> str:
    """Create an owner-only local token entry and return its raw value once."""

    if scope not in {"producer", "viewer", "admin"}:
        raise ValueError("scope must be producer, viewer, or admin")
    token_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    raw_token = secrets.token_urlsafe(32)
    try:
        entries = json.loads(token_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        entries = []
    entries.append({"hash": _hash(raw_token), "scope": scope, "source": source})
    temporary = token_file.with_suffix(".tmp")
    temporary.write_text(json.dumps(entries, separators=(",", ":")), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(token_file)
    token_file.chmod(0o600)
    return raw_token
