from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: Literal["local", "test", "production"] = "local"
    LOG_LEVEL: str = "INFO"
    # JSON é o default (log estruturado). Ponha false para ler colorido no terminal.
    LOG_JSON: bool = True

    DATABASE_URL: str = "postgresql://wallet:wallet@localhost:5432/wallet"
    DB_POOL_MIN: int = 1
    DB_POOL_MAX: int = 10

    JWT_SECRET: SecretStr = SecretStr("dev-secret-nao-use-em-producao")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 7

    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4

    @property
    def asyncpg_dsn(self) -> str:
        """asyncpg fala o protocolo direto, sem prefixo de driver."""
        return self.DATABASE_URL

    @property
    def alembic_dsn(self) -> str:
        """SQLAlchemy (que o Alembic usa por baixo) exige o driver explícito no schema da URL."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
