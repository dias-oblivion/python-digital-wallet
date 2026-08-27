"""Envelope de erro — o mesmo formato para erro de domínio, de validação e inesperado."""

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str = Field(examples=["conflict"])
    message: str = Field(examples=["e-mail já cadastrado"])
    details: dict[str, object] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody
    request_id: str | None = None
