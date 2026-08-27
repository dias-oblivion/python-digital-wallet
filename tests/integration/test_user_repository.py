"""O contrato `UserRepository` exercitado contra Postgres de verdade.

É o teste que os fakes não substituem: SQL, índice único, tipos e mapeamento de linha.
"""

from uuid import uuid4

import pytest

from wallet.core.errors import ConflictError
from wallet.db.connection import DbConnection
from wallet.db.repositories.user import PgUserRepository
from wallet.models.user import User


def make_user(email: str = "ana@example.com") -> User:
    return User.new(email=email, password_hash="$argon2-fake", full_name="Ana Souza")


async def test_add_e_by_id_preservam_todos_os_campos(conn: DbConnection) -> None:
    repo = PgUserRepository(conn)
    user = make_user()

    await repo.add(user)
    found = await repo.by_id(user.id)

    assert found is not None
    assert found == user  # inclui timestamps com timezone e o UUID


async def test_by_id_inexistente_devolve_none(conn: DbConnection) -> None:
    assert await PgUserRepository(conn).by_id(uuid4()) is None


async def test_by_email_ignora_a_caixa(conn: DbConnection) -> None:
    """Confirma que a query casa com o índice único sobre lower(email)."""
    repo = PgUserRepository(conn)
    await repo.add(make_user("ana@example.com"))

    assert await repo.by_email("ANA@EXAMPLE.COM") is not None
    assert await repo.by_email("  Ana@Example.com  ".strip()) is not None


async def test_email_duplicado_viola_o_indice_e_vira_conflito(conn: DbConnection) -> None:
    """A janela de corrida que o service não cobre: o banco é a última linha de defesa."""
    repo = PgUserRepository(conn)
    await repo.add(make_user("ana@example.com"))

    with pytest.raises(ConflictError):
        await repo.add(make_user("ANA@EXAMPLE.COM"))
