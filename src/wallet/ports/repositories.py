"""Contratos de persistência.

Fala apenas em entidades de domínio — nenhuma menção a asyncpg, SQL ou conexão. `Protocol` é
structural typing: as implementações NÃO herdam daqui e não se registram em lugar nenhum; se as
assinaturas batem, o contrato está satisfeito, e o mypy verifica isso em `api/wiring.py`.
"""

from typing import Protocol
from uuid import UUID

from wallet.models.user import User


class UserRepository(Protocol):
    async def by_id(self, user_id: UUID) -> User | None: ...

    async def by_email(self, email: str) -> User | None:
        """Busca case-insensitive — o e-mail é normalizado pelo service antes de chegar aqui."""
        ...

    async def add(self, user: User) -> None: ...
