"""Regras de usuário. Hoje é fino de propósito — é aqui que entram as regras de perfil."""

from uuid import UUID

from core.errors import NotFoundError
from models.user import User
from ports.repositories import UserRepository


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def by_id(self, user_id: UUID) -> User:
        """Diferente do repositório, que devolve None: aqui a ausência é um erro de domínio."""
        user = await self._users.by_id(user_id)
        if user is None:
            raise NotFoundError("usuário não encontrado", user_id=str(user_id))
        return user
