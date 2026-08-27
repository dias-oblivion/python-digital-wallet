"""Main Component — a composição app-scoped, na camada mais externa.

É o único lugar que cria recursos de vida longa (pool, logging). Ninguém importa este módulo:
ele importa todo mundo. Composição por request fica em `api/wiring.py`.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from wallet.api.handlers import register_exception_handlers
from wallet.api.middleware import RequestContextMiddleware
from wallet.api.router import api_router
from wallet.api.routers import health
from wallet.core.config import Settings, get_settings
from wallet.core.logging import configure_logging
from wallet.db.pool import close_pool, create_pool

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    app.state.pool = await create_pool(settings)
    logger.info("app_iniciada", env=settings.APP_ENV, pool_max=settings.DB_POOL_MAX)
    try:
        yield
    finally:
        await close_pool(app.state.pool)
        logger.info("app_encerrada")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL, json_output=settings.LOG_JSON)

    app = FastAPI(
        title="digital wallet",
        version="0.1.0",
        summary="API REST de carteira digital — FastAPI + asyncpg, em camadas com DIP",
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(api_router)
    return app


app = create_app()
