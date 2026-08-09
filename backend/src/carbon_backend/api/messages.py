"""Producer message registration endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from carbon_backend.auth.tokens import TokenPrincipal, authenticate
from carbon_backend.domain.messages import ProducerMessage
from carbon_backend.errors import ApiError
from carbon_backend.repositories.messages import MessageRepository
from carbon_backend.services.registration import RegistrationService
from carbon_backend.storage.vault import VaultStorage

router = APIRouter(prefix="/messages", tags=["messages"])


class RegistrationResponse(BaseModel):
    """Minimal response for a registered or replayed producer message."""

    public_id: str


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
    return RegistrationResponse(public_id=identifier)
