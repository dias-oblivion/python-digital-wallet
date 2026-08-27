"""Aliases de tipo para o acesso ao Postgres.

Dois detalhes do asyncpg que valem conhecer:

1. `pool.acquire()` NÃO devolve uma `Connection` — devolve um `PoolConnectionProxy`, que expõe a
   mesma interface por delegação. Os dois aparecem no projeto: o proxy em produção (via pool) e a
   `Connection` crua nos testes que abrem conexão direta. `DbConnection` aceita ambos.

2. `Connection` e `Pool` são genéricos apenas nos STUBS (`asyncpg-stubs`); em runtime
   `asyncpg.Pool[...]` levanta `TypeError: type 'Pool' is not subscriptable`. Por isso o bloco
   `TYPE_CHECKING`: o mypy vê os parâmetros de tipo, o interpretador vê a classe crua.
"""

from typing import TYPE_CHECKING, TypeAlias

import asyncpg
from asyncpg.pool import PoolConnectionProxy

if TYPE_CHECKING:
    DbConnection: TypeAlias = (  # noqa: UP040 — `type` não permite o par TYPE_CHECKING/runtime
        asyncpg.Connection[asyncpg.Record] | PoolConnectionProxy[asyncpg.Record]
    )
    DbPool: TypeAlias = asyncpg.Pool[asyncpg.Record]  # noqa: UP040
else:
    DbConnection = asyncpg.Connection
    DbPool = asyncpg.Pool
