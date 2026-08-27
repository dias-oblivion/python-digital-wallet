"""Garante o contrato do log: uma linha JSON por evento, com o contexto vinculado.

Sem isso, uma mudança de configuração silenciosa derruba a observabilidade sem quebrar teste algum
— foi o que aconteceu durante a construção deste projeto.
"""

import json
import logging
from collections.abc import Iterator

import pytest
import structlog

from core.logging import configure_logging


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    """configure_logging troca os handlers do root logger — restaura para não vazar
    um handler apontando para o stdout capturado do pytest nos testes seguintes."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    try:
        yield
    finally:
        structlog.reset_defaults()
        structlog.contextvars.clear_contextvars()
        root.handlers, root.level = handlers, level


def test_evento_sai_como_uma_linha_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json_output=True)

    structlog.get_logger("teste").info("request", method="GET", status=200)

    line = capsys.readouterr().out.strip()
    payload = json.loads(line)  # falha se não for JSON válido
    assert payload["event"] == "request"
    assert payload["method"] == "GET"
    assert payload["status"] == 200
    assert payload["level"] == "info"
    assert payload["timestamp"]


def test_contexto_vinculado_aparece_em_todos_os_eventos(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """É assim que o request_id chega a cada log do request, sem ser passado à mão."""
    configure_logging("INFO", json_output=True)
    structlog.contextvars.bind_contextvars(request_id="abc-123")

    structlog.get_logger("teste").info("primeiro")
    structlog.get_logger("teste").info("segundo")

    lines = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert [entry["request_id"] for entry in lines] == ["abc-123", "abc-123"]


def test_modo_console_nao_emite_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO", json_output=False)

    structlog.get_logger("teste").info("request")

    with pytest.raises(json.JSONDecodeError):
        json.loads(capsys.readouterr().out.strip())
