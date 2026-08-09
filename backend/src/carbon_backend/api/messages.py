"""Producer message registration endpoint."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from carbon_backend.auth.tokens import TokenPrincipal, authenticate
from carbon_backend.domain.messages import ProducerMessage
from carbon_backend.errors import ApiError
from carbon_backend.repositories.messages import MessageRepository
from carbon_backend.services.lifecycle import LifecycleService
from carbon_backend.services.registration import RegistrationService
from carbon_backend.storage.vault import VaultStorage

router = APIRouter(prefix="/messages", tags=["messages"])


class RegistrationResponse(BaseModel):
    """Minimal response for a registered or replayed producer message."""

    public_id: str


class MessageSummary(BaseModel):
    """List representation of an active message."""

    public_id: str
    source: str
    title: str
    occurred_at: datetime
    received_at: datetime
    read_at: datetime | None
    tags: list[str]


class MessageDetail(MessageSummary):
    """Full active message representation."""

    source_event_id: str | None
    body_markdown: str


class SearchResponse(BaseModel):
    """Ranked search page with an opaque cursor."""

    items: list[MessageSummary]
    next_cursor: str | None


class MessageListResponse(BaseModel):
    """Cursor page of active messages and the global unread indicator."""

    items: list[MessageSummary]
    next_cursor: str | None
    unread_count: int


def producer_principal(
    request: Request, authorization: str | None = Header(default=None)
) -> TokenPrincipal:
    """Require a local producer bearer token."""

    if authorization is None or not authorization.startswith("Bearer "):
        raise ApiError(
            status_code=401, code="authentication_required", message="Authentication required"
        )
    return authenticate(
        request.app.state.settings.token_file, authorization.removeprefix("Bearer "), "producer"
    )


ProducerPrincipal = Annotated[TokenPrincipal, Depends(producer_principal)]


def viewer_principal(
    request: Request, authorization: str | None = Header(default=None)
) -> TokenPrincipal:
    """Require a local viewer bearer token."""

    if authorization is None or not authorization.startswith("Bearer "):
        raise ApiError(
            status_code=401, code="authentication_required", message="Authentication required"
        )
    return authenticate(
        request.app.state.settings.token_file, authorization.removeprefix("Bearer "), "viewer"
    )


ViewerPrincipal = Annotated[TokenPrincipal, Depends(viewer_principal)]


def _decode_cursor(value: str | None) -> tuple[datetime | None, str | None]:
    if value is None:
        return None, None
    try:
        payload = json.loads(base64.urlsafe_b64decode(value.encode()).decode())
        return datetime.fromisoformat(payload["received_at"]), payload["public_id"]
    except (KeyError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ApiError(
            status_code=422, code="validation_error", message="Cursor is invalid"
        ) from error


def _encode_cursor(item: MessageSummary) -> str:
    payload = {"received_at": item.received_at.isoformat(), "public_id": item.public_id}
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()


@router.get("/search", response_model=SearchResponse)
async def search_messages(
    request: Request,
    _: ViewerPrincipal,
    q: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
) -> SearchResponse:
    """Search active messages by FTS and trigram similarity."""

    received_at, public_id = _decode_cursor(cursor)
    rows = await MessageRepository(request.app.state.engine).search_active(
        q, limit, received_at, public_id
    )
    items = [MessageSummary.model_validate(row) for row in rows]
    next_cursor = _encode_cursor(items[-1]) if len(items) == limit else None
    return SearchResponse(items=items, next_cursor=next_cursor)


@router.get("", response_model=MessageListResponse)
async def list_messages(
    request: Request,
    _: ViewerPrincipal,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    source: str | None = Query(default=None, min_length=1, max_length=32),
    unread: bool | None = None,
) -> MessageListResponse:
    """List one filtered active-message cursor page."""

    received_at, public_id = _decode_cursor(cursor)
    repository = MessageRepository(request.app.state.engine)
    rows = await repository.list_active(limit, received_at, public_id, source, unread)
    items = [MessageSummary.model_validate(item) for item in rows]
    return MessageListResponse(
        items=items,
        next_cursor=_encode_cursor(items[-1]) if len(items) == limit else None,
        unread_count=await repository.unread_count(),
    )


@router.get("/{public_id}", response_model=MessageDetail)
async def get_message(public_id: str, request: Request, _: ViewerPrincipal) -> MessageDetail:
    """Return one active message."""

    message = await MessageRepository(request.app.state.engine).get_active(public_id)
    if message is None:
        raise ApiError(status_code=404, code="not_found", message="Message was not found")
    return MessageDetail.model_validate(message)


@router.post("/{public_id}/read", status_code=204)
async def mark_read(public_id: str, request: Request, _: ViewerPrincipal) -> Response:
    """Mark an active message as read."""

    service = LifecycleService(
        MessageRepository(request.app.state.engine),
        VaultStorage(request.app.state.settings.vault_root),
    )
    if not await service.set_read_state(public_id, read=True):
        raise ApiError(status_code=404, code="not_found", message="Message was not found")
    await request.app.state.event_broker.publish("message.read", public_id)
    return Response(status_code=204)


@router.post("/{public_id}/unread", status_code=204)
async def mark_unread(public_id: str, request: Request, _: ViewerPrincipal) -> Response:
    """Mark an active message as unread."""

    service = LifecycleService(
        MessageRepository(request.app.state.engine),
        VaultStorage(request.app.state.settings.vault_root),
    )
    if not await service.set_read_state(public_id, read=False):
        raise ApiError(status_code=404, code="not_found", message="Message was not found")
    await request.app.state.event_broker.publish("message.unread", public_id)
    return Response(status_code=204)


@router.delete("/{public_id}", status_code=204)
async def delete_message(public_id: str, request: Request, _: ViewerPrincipal) -> Response:
    """Recoverably delete one message by moving its canonical file to trash."""

    service = LifecycleService(
        MessageRepository(request.app.state.engine),
        VaultStorage(request.app.state.settings.vault_root),
    )
    if not await service.delete(public_id):
        raise ApiError(status_code=404, code="not_found", message="Message was not found")
    await request.app.state.event_broker.publish("message.deleted", public_id)
    return Response(status_code=204)


@router.post("", response_model=RegistrationResponse, status_code=201)
async def register_message(
    payload: ProducerMessage,
    response: Response,
    request: Request,
    principal: ProducerPrincipal,
) -> RegistrationResponse:
    """Register one authenticated producer message."""

    if principal.source is not None and principal.source != payload.source:
        raise ApiError(
            status_code=403, code="forbidden", message="Token cannot register this source"
        )
    service = RegistrationService(
        MessageRepository(request.app.state.engine),
        VaultStorage(request.app.state.settings.vault_root),
    )
    try:
        identifier, replay = await service.register(payload)
    except OSError as error:
        raise ApiError(
            status_code=503, code="storage_error", message="Vault write failed"
        ) from error
    except SQLAlchemyError as error:
        raise ApiError(
            status_code=503, code="projection_error", message="Database write failed"
        ) from error
    if replay:
        response.status_code = 200
        response.headers["X-Idempotent-Replay"] = "true"
    else:
        await request.app.state.event_broker.publish("message.created", identifier)
    return RegistrationResponse(public_id=identifier)
