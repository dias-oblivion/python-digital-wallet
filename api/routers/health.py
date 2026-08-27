"""Health checks fora do prefixo versionado: são sobre o processo, não sobre a API de negócio."""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from api.wiring import DatabaseHealthDep

router = APIRouter(prefix="/health", tags=["health"])


class LiveResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    database: str


@router.get("/live")
async def live() -> LiveResponse:
    """O processo está de pé. Não toca em dependência externa — de propósito."""
    return LiveResponse(status="ok")


@router.get("/ready")
async def ready(database_ok: DatabaseHealthDep, response: Response) -> ReadyResponse:
    """Pronto para receber tráfego: exige o banco respondendo."""
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(
        status="ok" if database_ok else "degraded",
        database="ok" if database_ok else "unreachable",
    )
