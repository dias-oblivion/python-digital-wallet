"""Representação de tokens no domínio. `TokenClaims` dá forma tipada ao payload do JWT,
que o PyJWT devolve como dict[str, Any] cru."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

TokenType = Literal["access", "refresh"]


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(frozen=True, slots=True)
class TokenClaims:
    subject: UUID
    token_type: TokenType
    jti: str
    issued_at: datetime
    expires_at: datetime
