"""Implementação in-memory do MESMO Protocol que o PgUserRepository satisfaz.

Não herda de `UserRepository` nem se registra em nada — structural typing basta, e o mypy confirma
a conformidade onde o fake é usado.
"""

from collections.abc import Iterable
from uuid import UUID

from models.user import User


class InMemoryUserRepository:
    def __init__(self, users: Iterable[User] = ()) -> None:
        self._by_id: dict[UUID, User] = {user.id: user for user in users}

    async def by_id(self, user_id: UUID) -> User | None:
        return self._by_id.get(user_id)

    async def by_email(self, email: str) -> User | None:
        target = email.strip().lower()
        return next(
            (user for user in self._by_id.values() if user.email.strip().lower() == target),
            None,
        )

    async def add(self, user: User) -> None:
        self._by_id[user.id] = user

    # --- helpers de teste, fora do Protocol ---

    def count(self) -> int:
        return len(self._by_id)
