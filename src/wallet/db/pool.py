"""Ciclo de vida do pool asyncpg.

Não importa FastAPI: as dependências de request (`get_conn`, `get_tx_conn`) vivem em
`api/wiring.py`, do lado de fora. Aqui é só criação, encerramento e registro de codecs.
"""

import asyncpg

from wallet.core.config import Settings
from wallet.db.connection import DbPool


async def create_pool(settings: Settings) -> DbPool:
    return await asyncpg.create_pool(
        dsn=settings.asyncpg_dsn,
        min_size=settings.DB_POOL_MIN,
        max_size=settings.DB_POOL_MAX,
        command_timeout=30,
    )


async def close_pool(pool: DbPool) -> None:
    await pool.close()


async def check_connection(pool: DbPool) -> bool:
    """Usado pelo /health/ready — falha rápido em vez de derrubar o processo."""
    try:
        async with pool.acquire() as conn:
            return bool(await conn.fetchval("SELECT 1") == 1)
    except (asyncpg.PostgresError, OSError):
        return False
