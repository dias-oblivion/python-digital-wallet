from uuid import uuid4

import pytest

from tests.fakes.repositories import InMemoryUserRepository
from wallet.core.errors import NotFoundError
from wallet.models.user import User
from wallet.services.users import UserService


async def test_by_id_devolve_o_usuario() -> None:
    user = User.new(email="ana@example.com", password_hash="x", full_name="Ana Souza")
    service = UserService(users=InMemoryUserRepository([user]))

    assert (await service.by_id(user.id)).email == "ana@example.com"


async def test_by_id_inexistente_levanta_erro_de_dominio() -> None:
    """O repositório devolve None; traduzir isso em erro é regra, não infraestrutura."""
    service = UserService(users=InMemoryUserRepository())

    with pytest.raises(NotFoundError):
        await service.by_id(uuid4())
