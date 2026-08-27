"""Implementação asyncpg do contrato `ports.repositories.UserRepository`.

Não herda do Protocol e não se registra em nada: as assinaturas batendo já bastam, e o mypy
confirma a conformidade em `api/wiring.py`. Recebe a conexão pelo construtor — não sabe o que é
pool, request ou transação.
"""

from uuid import UUID

import asyncpg

from wallet.core.errors import ConflictError
from wallet.db.connection import DbConnection
from wallet.db.schemas import user as schema
from wallet.models.user import User


class PgUserRepository:
    def __init__(self, conn: DbConnection) -> None:
        self._conn = conn

    async def by_id(self, user_id: UUID) -> User | None:
        record = await self._conn.fetchrow(
            f"SELECT {schema.COLUMNS} FROM {schema.TABLE} WHERE id = $1",
            user_id,
        )
        return schema.to_user(record) if record is not None else None

    async def by_email(self, email: str) -> User | None:
        # lower(email) casa com o índice único criado na migration
        record = await self._conn.fetchrow(
            f"SELECT {schema.COLUMNS} FROM {schema.TABLE} WHERE lower(email) = lower($1)",
            email,
        )
        return schema.to_user(record) if record is not None else None

    async def add(self, user: User) -> None:
        try:
            await self._conn.execute(
                f"INSERT INTO {schema.TABLE} ({schema.COLUMNS}) VALUES ({schema.PLACEHOLDERS})",
                user.id,
                user.email,
                user.password_hash,
                user.full_name,
                user.is_active,
                user.created_at,
                user.updated_at,
            )
        except asyncpg.UniqueViolationError as exc:
            # o service já checa duplicidade antes; isto fecha a janela de corrida entre
            # duas requisições simultâneas com o mesmo e-mail
            raise ConflictError("e-mail já cadastrado", field="email") from exc
