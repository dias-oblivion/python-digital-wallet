"""Entidade de domínio. Não importa nada do projeto, nem bibliotecas de terceiros."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: str
    password_hash: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new(cls, *, email: str, password_hash: str, full_name: str) -> "User":
        """Cria um usuário novo já com id e timestamps — antes de qualquer persistência."""
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def deactivate(self) -> "User":
        return replace(self, is_active=False, updated_at=datetime.now(UTC))

    def with_password_hash(self, password_hash: str) -> "User":
        return replace(self, password_hash=password_hash, updated_at=datetime.now(UTC))
