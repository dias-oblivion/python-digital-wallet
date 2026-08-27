"""Tradução erro de domínio -> resposta HTTP.

Esta é a única camada que conhece status codes. `core/errors.py` permanece puro, e é por isso que
o service pode levantar `ConflictError` sem nunca importar FastAPI.
"""

from typing import Final

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from wallet.api.schemas.errors import ErrorBody, ErrorResponse
from wallet.core.errors import (
    AppError,
    AuthenticationError,
    ConflictError,
    DomainValidationError,
    NotFoundError,
    PermissionDeniedError,
)

logger = structlog.get_logger(__name__)

STATUS_BY_ERROR: Final[dict[type[AppError], int]] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    DomainValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


def _envelope(
    request: Request, *, code: str, message: str, details: dict[str, object], status_code: int
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details),
        request_id=_request_id(request),
    )
    headers = (
        {"WWW-Authenticate": "Bearer"} if status_code == status.HTTP_401_UNAUTHORIZED else None
    )
    return JSONResponse(
        status_code=status_code, content=body.model_dump(mode="json"), headers=headers
    )


async def handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    status_code = STATUS_BY_ERROR.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    return _envelope(
        request,
        code=exc.code,
        message=exc.message,
        details=dict(exc.details),
        status_code=status_code,
    )


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """Erro de schema no mesmo envelope dos erros de domínio — um formato só para o cliente."""
    assert isinstance(exc, RequestValidationError)
    fields = [
        {"field": ".".join(str(part) for part in error["loc"][1:]), "reason": error["msg"]}
        for error in exc.errors()
    ]
    return _envelope(
        request,
        code="validation_error",
        message="dados inválidos",
        details={"fields": fields},
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Rede de segurança: loga o stack completo e devolve uma mensagem genérica."""
    logger.exception("erro_inesperado", path=request.url.path, error=type(exc).__name__)
    return _envelope(
        request,
        code="internal_error",
        message="erro interno",
        details={},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
