from datetime import timedelta
from uuid import uuid4

import pytest

from wallet.core.errors import AuthenticationError
from wallet.core.security import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_nao_guarda_a_senha_em_claro() -> None:
    hashed = hash_password("senha-forte-123")
    assert "senha-forte-123" not in hashed
    assert hashed.startswith("$argon2")


def test_hash_da_mesma_senha_gera_valores_diferentes() -> None:
    """Argon2 usa salt aleatório: hashes iguais indicariam salt fixo."""
    assert hash_password("senha-forte-123") != hash_password("senha-forte-123")


def test_verify_aceita_a_senha_correta_e_recusa_a_errada() -> None:
    hashed = hash_password("senha-forte-123")
    assert verify_password(hashed, "senha-forte-123") is True
    assert verify_password(hashed, "senha-errada-123") is False


def test_verify_com_hash_malformado_retorna_false_em_vez_de_explodir() -> None:
    assert verify_password("nao-e-um-hash", "senha-forte-123") is False


def test_access_token_carrega_o_subject() -> None:
    user_id = uuid4()
    claims = decode_token(create_access_token(user_id), expected_type="access")
    assert claims.subject == user_id
    assert claims.token_type == "access"
    assert claims.expires_at > claims.issued_at


def test_token_expirado_e_recusado() -> None:
    """TTL negativo produz um token já vencido — dispensa abstrair o relógio."""
    token = create_access_token(uuid4(), ttl=timedelta(seconds=-1))
    with pytest.raises(AuthenticationError, match="expirado"):
        decode_token(token, expected_type="access")


def test_refresh_token_nao_serve_como_access_token() -> None:
    token = create_refresh_token(uuid4())
    with pytest.raises(AuthenticationError, match="tipo de token"):
        decode_token(token, expected_type="access")


def test_token_adulterado_e_recusado() -> None:
    token = create_access_token(uuid4())
    with pytest.raises(AuthenticationError, match="inválido"):
        decode_token(token + "x", expected_type="access")


def test_par_de_tokens_traz_access_e_refresh_distintos() -> None:
    user_id = uuid4()
    pair = create_token_pair(user_id)
    assert pair.access_token != pair.refresh_token
    assert decode_token(pair.access_token, expected_type="access").subject == user_id
    assert decode_token(pair.refresh_token, expected_type="refresh").subject == user_id
