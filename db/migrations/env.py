"""Alembic sobre asyncpg.

Duas escolhas deliberadas aqui:

1. A DSN vem de `Settings` (que lê `.env`/ambiente), nunca do `alembic.ini` — um só lugar
   define onde o banco está. O Alembic usa SQLAlchemy por baixo, e SQLAlchemy exige o driver
   explícito no schema da URL: `postgresql+asyncpg://`.
2. `target_metadata = None` porque o projeto não tem modelos SQLAlchemy. Logo
   `alembic revision --autogenerate` NÃO funciona: as migrations são escritas à mão, com SQL
   nativo. É o custo — e o exercício — de não usar ORM.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from core.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().alembic_dsn)

target_metadata = None


def run_migrations_offline() -> None:
    """Gera o SQL sem conectar (`alembic upgrade head --sql`)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    # asyncio.run: por isso a fixture de teste que aplica as migrations precisa ser SÍNCRONA
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
