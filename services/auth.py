"""Regras de autenticação.

Recebe o repositório pelo construtor e o conhece apenas pelo Protocol: em produção chega um
`PgUserRepository`, no teste um `InMemoryUserRepository`, e este arquivo não sabe a diferença.
Nada de FastAPI, asyncpg ou transação aqui.
"""

from core.errors import AuthenticationError, ConflictError, DomainValidationError
from core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from models.token import TokenPair
from models.user import User
from ports.repositories import UserRepository

MIN_PASSWORD_LENGTH = 12


def normalize_email(raw: str) -> str:
    return raw.strip().lower()


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def register(self, *, email: str, password: str, full_name: str) -> User:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise DomainValidationError(
                f"a senha deve ter ao menos {MIN_PASSWORD_LENGTH} caracteres", field="password"
            )

        normalized = normalize_email(email)
        if await self._users.by_email(normalized) is not None:
            raise ConflictError("e-mail já cadastrado", field="email")

        user = User.new(
            email=normalized,
            password_hash=hash_password(password),
            full_name=full_name.strip(),
        )
        await self._users.add(user)
        return user

    async def login(self, *, email: str, password: str) -> TokenPair:
        user = await self._users.by_email(normalize_email(email))
        # mensagem única para e-mail inexistente e senha errada: não revela quem tem conta
        if user is None or not verify_password(user.password_hash, password):
            raise AuthenticationError("credenciais inválidas")
        if not user.is_active:
            raise AuthenticationError("conta inativa")
        return create_token_pair(user.id)

    async def refresh(self, refresh_token: str) -> TokenPair:
        claims = decode_token(refresh_token, expected_type="refresh")
        user = await self._users.by_id(claims.subject)
        if user is None or not user.is_active:
            raise AuthenticationError("token não corresponde a um usuário ativo")
        return create_token_pair(user.id)

    async def authenticate(self, access_token: str) -> User:
        """Resolve o portador de um access token. Usado pela dependência de autenticação."""
        claims = decode_token(access_token, expected_type="access")
        user = await self._users.by_id(claims.subject)
        if user is None or not user.is_active:
            raise AuthenticationError("token não corresponde a um usuário ativo")
        return user
