"""COMPOSITION ROOT (request-scoped).

O único módulo que sabe, ao mesmo tempo, qual é o contrato e qual é a implementação concreta.
Routers só veem os aliases `Annotated[...]`; services só veem os Protocols.

Repare no padrão de cada provider: a ASSINATURA declara o port, o CORPO instancia a impl. É isso
que faz o `mypy --strict` verificar aqui — uma única vez, no ponto onde abstrato e concreto se
encontram — que `PgUserRepository` satisfaz `UserRepository`, sem herança e sem registro manual.

Escopos de conexão:
  - `AuthService` recebe conexão TRANSACIONADA (tem operações de escrita).
  - `UserService` recebe conexão simples (só leitura).
"""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.errors import AuthenticationError
from db.connection import DbConnection, DbPool
from db.pool import check_connection
from db.repositories.user import PgUserRepository
from models.user import User
from ports.repositories import UserRepository
from services.auth import AuthService
from services.users import UserService

# ----------------------------------------------------------------- conexão


def get_pool(request: Request) -> DbPool:
    """O pool é app-scoped: criado uma vez no lifespan de `main.py`."""
    return cast("DbPool", request.app.state.pool)


PoolDep = Annotated[DbPool, Depends(get_pool)]


async def get_conn(pool: PoolDep) -> AsyncIterator[DbConnection]:
    """Conexão para leitura — devolvida ao pool no fim do request."""
    async with pool.acquire() as conn:
        yield conn


async def get_tx_conn(pool: PoolDep) -> AsyncIterator[DbConnection]:
    """Conexão para escrita: COMMIT no fim do request, ROLLBACK se qualquer exceção subir.

    É este `async with` que substitui a Unit of Work — e é o que vai segurar a transferência
    atômica (debita + credita + grava ledger) quando `transactions` entrar.
    """
    async with pool.acquire() as conn, conn.transaction():
        yield conn


ConnDep = Annotated[DbConnection, Depends(get_conn)]
TxConnDep = Annotated[DbConnection, Depends(get_tx_conn)]


async def get_database_health(pool: PoolDep) -> bool:
    """O router de health pergunta "o banco responde?" — sem saber que existe asyncpg."""
    return await check_connection(pool)


DatabaseHealthDep = Annotated[bool, Depends(get_database_health)]

# ----------------------------------------------------------------- repositórios


def get_user_repository(conn: ConnDep) -> UserRepository:
    return PgUserRepository(conn)


def get_tx_user_repository(conn: TxConnDep) -> UserRepository:
    return PgUserRepository(conn)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
TxUserRepoDep = Annotated[UserRepository, Depends(get_tx_user_repository)]

# ----------------------------------------------------------------- services


def get_auth_service(users: TxUserRepoDep) -> AuthService:
    return AuthService(users=users)


def get_user_service(users: UserRepoDep) -> UserService:
    return UserService(users=users)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]

# ----------------------------------------------------------------- autenticação

_bearer = HTTPBearer(auto_error=False, description="Bearer <access_token>")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: AuthServiceDep,
) -> User:
    if credentials is None:
        raise AuthenticationError("token de acesso ausente")
    return await auth.authenticate(credentials.credentials)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
