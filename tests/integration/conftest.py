"""Postgres real via Testcontainers.

Duas decisões que valem explicar:

1. A fixture que aplica as migrations é SÍNCRONA de propósito. `migrations/env.py` chama
   `asyncio.run()`, que levanta `RuntimeError` se for invocado de dentro de um event loop já
   ativo — o que aconteceria numa fixture `async`.

2. Cada teste roda dentro de uma transação que é revertida no fim (`tx.rollback()`). Isso dá
   isolamento total sem `TRUNCATE` entre testes, e o banco volta ao estado da migration.
"""

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from testcontainers.community.postgres import PostgresContainer

from api.wiring import get_conn, get_pool, get_tx_conn
from core.config import get_settings
from db.connection import DbConnection, DbPool
from main import create_app

ROOT = Path(__file__).resolve().parents[2]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Marca tudo neste diretório como `integration` — permite `pytest -m "not integration"`."""
    for item in items:
        if "integration" in str(item.path):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    # driver=None => DSN no formato postgresql://, que é o que o asyncpg espera
    with PostgresContainer("postgres:17-alpine", driver=None) as container:
        dsn = container.get_connection_url()
        os.environ["DATABASE_URL"] = dsn
        get_settings.cache_clear()  # Settings é @lru_cache: sem isso a DSN antiga persiste
        try:
            yield dsn
        finally:
            os.environ.pop("DATABASE_URL", None)
            get_settings.cache_clear()


@pytest.fixture(scope="session")
def migrated_database(database_url: str) -> str:
    """Roda `alembic upgrade head` — o mesmo caminho usado em produção."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "db" / "migrations"))
    command.upgrade(config, "head")
    return database_url


@pytest.fixture
async def conn(migrated_database: str) -> AsyncIterator[DbConnection]:
    connection = await asyncpg.connect(migrated_database)
    transaction = connection.transaction()
    await transaction.start()
    try:
        yield connection
    finally:
        await transaction.rollback()
        await connection.close()


@pytest.fixture
async def pool(migrated_database: str) -> AsyncIterator[DbPool]:
    created = await asyncpg.create_pool(migrated_database, min_size=1, max_size=2)
    assert created is not None
    try:
        yield created
    finally:
        await created.close()


@pytest.fixture
async def client(conn: DbConnection, pool: DbPool) -> AsyncIterator[AsyncClient]:
    """App real, com as dependências de conexão apontando para a transação do teste.

    Só isto é substituído: routers, wiring, services e repositórios são os de produção.
    """
    app = create_app()
    app.dependency_overrides[get_conn] = lambda: conn
    app.dependency_overrides[get_tx_conn] = lambda: conn
    app.dependency_overrides[get_pool] = lambda: pool

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
