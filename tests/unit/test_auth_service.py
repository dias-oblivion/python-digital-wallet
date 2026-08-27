"""Regra de negócio testada sem Docker, sem Postgres, sem FastAPI e sem um único mock.

O wiring é feito na mão, aqui mesmo: é exatamente isso que a inversão de dependência compra.
"""

import pytest

from core.errors import AuthenticationError, ConflictError, DomainValidationError
from core.security import decode_token, verify_password
from models.user import User
from services.auth import AuthService
from tests.fakes.repositories import InMemoryUserRepository

SENHA = "senha-forte-123"


def make_service(*users: User) -> tuple[AuthService, InMemoryUserRepository]:
    repo = InMemoryUserRepository(users)
    return AuthService(users=repo), repo


def make_user(*, email: str = "ana@example.com", is_active: bool = True) -> User:
    from core.security import hash_password

    user = User.new(email=email, password_hash=hash_password(SENHA), full_name="Ana Souza")
    return user if is_active else user.deactivate()


# ------------------------------------------------------------------ register


async def test_register_persiste_o_usuario_com_a_senha_hasheada() -> None:
    service, repo = make_service()

    user = await service.register(email="ana@example.com", password=SENHA, full_name="Ana Souza")

    assert repo.count() == 1
    assert user.password_hash != SENHA
    assert verify_password(user.password_hash, SENHA)
    assert user.is_active is True


async def test_register_normaliza_email_e_nome() -> None:
    service, _ = make_service()

    user = await service.register(
        email="  Ana@Example.COM  ", password=SENHA, full_name="  Ana Souza  "
    )

    assert user.email == "ana@example.com"
    assert user.full_name == "Ana Souza"


async def test_register_recusa_email_ja_cadastrado_ignorando_caixa() -> None:
    service, repo = make_service(make_user(email="ana@example.com"))

    with pytest.raises(ConflictError):
        await service.register(email="ANA@EXAMPLE.COM", password=SENHA, full_name="Outra Ana")

    assert repo.count() == 1


async def test_register_recusa_senha_curta() -> None:
    service, repo = make_service()

    with pytest.raises(DomainValidationError):
        await service.register(email="ana@example.com", password="curta", full_name="Ana")

    assert repo.count() == 0


# ------------------------------------------------------------------ login


async def test_login_devolve_par_de_tokens_do_usuario() -> None:
    user = make_user()
    service, _ = make_service(user)

    pair = await service.login(email="ana@example.com", password=SENHA)

    assert decode_token(pair.access_token, expected_type="access").subject == user.id
    assert decode_token(pair.refresh_token, expected_type="refresh").subject == user.id


async def test_login_com_senha_errada_falha() -> None:
    service, _ = make_service(make_user())

    with pytest.raises(AuthenticationError):
        await service.login(email="ana@example.com", password="senha-errada-123")


async def test_login_com_email_inexistente_falha_com_a_mesma_mensagem() -> None:
    """Não revela se o e-mail existe: a mensagem é idêntica à de senha errada."""
    service, _ = make_service(make_user())

    with pytest.raises(AuthenticationError, match="credenciais inválidas"):
        await service.login(email="ninguem@example.com", password=SENHA)


async def test_login_de_conta_inativa_falha() -> None:
    service, _ = make_service(make_user(is_active=False))

    with pytest.raises(AuthenticationError, match="inativa"):
        await service.login(email="ana@example.com", password=SENHA)


# ------------------------------------------------------------------ refresh / authenticate


async def test_refresh_emite_novo_par() -> None:
    user = make_user()
    service, _ = make_service(user)
    pair = await service.login(email="ana@example.com", password=SENHA)

    renewed = await service.refresh(pair.refresh_token)

    assert decode_token(renewed.access_token, expected_type="access").subject == user.id


async def test_refresh_recusa_access_token() -> None:
    service, _ = make_service(make_user())
    pair = await service.login(email="ana@example.com", password=SENHA)

    with pytest.raises(AuthenticationError, match="tipo de token"):
        await service.refresh(pair.access_token)


async def test_refresh_de_usuario_removido_falha() -> None:
    user = make_user()
    service, _ = make_service(user)
    pair = await service.login(email="ana@example.com", password=SENHA)

    orphan_service, _ = make_service()  # mesmo token, repositório vazio
    with pytest.raises(AuthenticationError, match="usuário ativo"):
        await orphan_service.refresh(pair.refresh_token)


async def test_authenticate_resolve_o_portador_do_token() -> None:
    user = make_user()
    service, _ = make_service(user)
    pair = await service.login(email="ana@example.com", password=SENHA)

    assert (await service.authenticate(pair.access_token)).id == user.id


async def test_authenticate_recusa_refresh_token() -> None:
    service, _ = make_service(make_user())
    pair = await service.login(email="ana@example.com", password=SENHA)

    with pytest.raises(AuthenticationError, match="tipo de token"):
        await service.authenticate(pair.refresh_token)
