from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from wallet.models.user import User


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        """Conversão explícita: `password_hash` não tem como escapar por descuido."""
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )
