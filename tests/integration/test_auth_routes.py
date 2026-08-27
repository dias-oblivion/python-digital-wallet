"""Fluxo HTTP ponta a ponta: router -> wiring -> service -> repositório -> Postgres.

Nada é mockado: as únicas peças substituídas são as dependências de conexão, que apontam para a
transação do teste.
"""

from typing import Any

from httpx import AsyncClient

SENHA = "senha-forte-123"
REGISTRO = {"email": "ana@example.com", "password": SENHA, "full_name": "Ana Souza"}


async def registrar(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/register", json={**REGISTRO, **overrides})
    return {"status": response.status_code, "body": response.json()}


async def autenticar(client: AsyncClient) -> str:
    await registrar(client)
    response = await client.post(
        "/api/v1/auth/login", json={"email": REGISTRO["email"], "password": SENHA}
    )
    token: str = response.json()["access_token"]
    return token


# ------------------------------------------------------------------ register


async def test_register_devolve_201_sem_expor_o_hash(client: AsyncClient) -> None:
    result = await registrar(client)

    assert result["status"] == 201
    assert result["body"]["email"] == "ana@example.com"
    assert result["body"]["is_active"] is True
    assert "password" not in result["body"]
    assert "password_hash" not in result["body"]


async def test_register_duplicado_devolve_409_no_envelope_padrao(client: AsyncClient) -> None:
    await registrar(client)

    result = await registrar(client, email="ANA@EXAMPLE.COM")

    assert result["status"] == 409
    assert result["body"]["error"]["code"] == "conflict"
    assert result["body"]["request_id"]  # o middleware preencheu o contexto


async def test_register_com_senha_curta_devolve_422_no_mesmo_envelope(
    client: AsyncClient,
) -> None:
    result = await registrar(client, password="curta")

    assert result["status"] == 422
    assert result["body"]["error"]["code"] == "validation_error"
    assert result["body"]["error"]["details"]["fields"][0]["field"] == "password"


async def test_register_com_email_invalido_devolve_422(client: AsyncClient) -> None:
    result = await registrar(client, email="nao-e-email")

    assert result["status"] == 422
    assert result["body"]["error"]["code"] == "validation_error"


# ------------------------------------------------------------------ login / refresh


async def test_login_devolve_os_dois_tokens(client: AsyncClient) -> None:
    await registrar(client)

    response = await client.post(
        "/api/v1/auth/login", json={"email": REGISTRO["email"], "password": SENHA}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_com_senha_errada_devolve_401(client: AsyncClient) -> None:
    await registrar(client)

    response = await client.post(
        "/api/v1/auth/login", json={"email": REGISTRO["email"], "password": "senha-errada-123"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"
    assert response.headers["www-authenticate"] == "Bearer"


async def test_refresh_troca_o_refresh_token_por_um_par_novo(client: AsyncClient) -> None:
    await registrar(client)
    login = await client.post(
        "/api/v1/auth/login", json={"email": REGISTRO["email"], "password": SENHA}
    )

    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login.json()["refresh_token"]}
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_recusa_um_access_token(client: AsyncClient) -> None:
    token = await autenticar(client)

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})

    assert response.status_code == 401


# ------------------------------------------------------------------ /users/me


async def test_me_devolve_o_usuario_do_token(client: AsyncClient) -> None:
    token = await autenticar(client)

    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "ana@example.com"


async def test_me_sem_token_devolve_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_me_com_token_invalido_devolve_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer nao-e-um-jwt"}
    )

    assert response.status_code == 401


async def test_resposta_traz_o_header_de_request_id(client: AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.headers["x-request-id"]
