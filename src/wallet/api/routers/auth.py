"""Borda HTTP de autenticação: traduz JSON <-> domínio e nada mais.

Nenhum import de `wallet.db` ou `asyncpg` aqui — quem escolhe a implementação é o `api/wiring.py`.
O `tests/test_architecture.py` falha se isso mudar.
"""

from fastapi import APIRouter, status

from wallet.api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from wallet.api.schemas.users import UserResponse
from wallet.api.wiring import AuthServiceDep

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, auth: AuthServiceDep) -> UserResponse:
    user = await auth.register(
        email=body.email,
        password=body.password.get_secret_value(),
        full_name=body.full_name,
    )
    return UserResponse.from_entity(user)


@router.post("/login")
async def login(body: LoginRequest, auth: AuthServiceDep) -> TokenResponse:
    pair = await auth.login(email=body.email, password=body.password.get_secret_value())
    return TokenResponse.from_pair(pair)


@router.post("/refresh")
async def refresh(body: RefreshRequest, auth: AuthServiceDep) -> TokenResponse:
    return TokenResponse.from_pair(await auth.refresh(body.refresh_token))
