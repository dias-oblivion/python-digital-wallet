"""A forma da LINHA no banco: nome da tabela, colunas e a tradução Record -> entidade.

Único lugar do projeto que conhece nomes de coluna. Nenhum `asyncpg.Record` escapa do pacote `db/`.
O DDL em si mora na migration — ela é a fonte da verdade; aqui só refletimos o que ela criou.
"""

from typing import Final

import asyncpg

from wallet.models.user import User

TABLE: Final = "users"
COLUMNS: Final = "id, email, password_hash, full_name, is_active, created_at, updated_at"
PLACEHOLDERS: Final = "$1, $2, $3, $4, $5, $6, $7"


def to_user(record: asyncpg.Record) -> User:
    return User(
        id=record["id"],
        email=record["email"],
        password_hash=record["password_hash"],
        full_name=record["full_name"],
        is_active=record["is_active"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )
