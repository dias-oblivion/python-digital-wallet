"""Hash de senha (Argon2) e emissão/validação de JWT (PyJWT).

Este módulo é deliberadamente PURO: CPU, determinístico, sem rede, sem banco, sem estado externo.
É por isso que `services/` pode importá-lo direto sem que isso atrapalhe teste nenhum — o
acoplamento que dói é com I/O, e esse continua invertido via `ports/`.

O custo do Argon2 vem de `Settings`: forte em produção, mínimo em `.env.test`, para a suíte não
arrastar. É o que dispensa um `PasswordHasher` abstrato só para testes.
"""

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any, cast
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from core.config import get_settings
from core.errors import AuthenticationError
from models.token import TokenClaims, TokenPair, TokenType


@lru_cache
def _hasher() -> PasswordHasher:
    s = get_settings()
    return PasswordHasher(
        time_cost=s.ARGON2_TIME_COST,
        memory_cost=s.ARGON2_MEMORY_COST,
        parallelism=s.ARGON2_PARALLELISM,
    )


def hash_password(raw_password: str) -> str:
    return _hasher().hash(raw_password)


def verify_password(password_hash: str, raw_password: str) -> bool:
    """False em vez de exceção: quem chama decide o que significa senha errada."""
    try:
        return _hasher().verify(password_hash, raw_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True quando o hash foi gerado com parâmetros mais fracos que os atuais."""
    return _hasher().check_needs_rehash(password_hash)


def _create_token(subject: UUID, token_type: TokenType, ttl: timedelta) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "typ": token_type,
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    return jwt.encode(payload, s.JWT_SECRET.get_secret_value(), algorithm=s.JWT_ALGORITHM)


def create_access_token(subject: UUID, ttl: timedelta | None = None) -> str:
    """`ttl` explícito existe para os testes: um TTL negativo produz um token já expirado,
    o que dispensa abstrair o relógio."""
    s = get_settings()
    return _create_token(subject, "access", ttl or timedelta(minutes=s.ACCESS_TOKEN_TTL_MINUTES))


def create_refresh_token(subject: UUID, ttl: timedelta | None = None) -> str:
    s = get_settings()
    return _create_token(subject, "refresh", ttl or timedelta(days=s.REFRESH_TOKEN_TTL_DAYS))


def create_token_pair(subject: UUID) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


def decode_token(token: str, *, expected_type: TokenType) -> TokenClaims:
    s = get_settings()
    try:
        payload = jwt.decode(
            token,
            s.JWT_SECRET.get_secret_value(),
            algorithms=[s.JWT_ALGORITHM],
            options={"require": ["sub", "typ", "jti", "iat", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("token expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("token inválido") from exc

    if payload["typ"] != expected_type:
        # impede usar um refresh token onde se espera um access token, e vice-versa
        raise AuthenticationError("tipo de token inválido")

    try:
        subject = UUID(payload["sub"])
    except ValueError as exc:
        raise AuthenticationError("token inválido") from exc

    return TokenClaims(
        subject=subject,
        token_type=cast(TokenType, payload["typ"]),
        jti=payload["jti"],
        issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
    )
