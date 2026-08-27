"""Erros de domínio — puros, sem qualquer noção de HTTP.

O mapeamento para status code vive em `api/handlers.py`. É isso que permite ao service levantar
`ConflictError` sem importar FastAPI.
"""

from typing import ClassVar


class AppError(Exception):
    code: ClassVar[str] = "internal_error"
    default_message: ClassVar[str] = "erro interno"

    def __init__(self, message: str | None = None, **details: object) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    code = "not_found"
    default_message = "recurso não encontrado"


class ConflictError(AppError):
    code = "conflict"
    default_message = "conflito com o estado atual do recurso"


class AuthenticationError(AppError):
    code = "unauthenticated"
    default_message = "credenciais inválidas"


class PermissionDeniedError(AppError):
    code = "permission_denied"
    default_message = "acesso negado"


class DomainValidationError(AppError):
    code = "validation_error"
    default_message = "dados inválidos"
