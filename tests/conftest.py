"""Carrega `.env.test` ANTES de qualquer `Settings` ser instanciada.

Variáveis de ambiente têm precedência sobre o `env_file` no pydantic-settings, então isso vence um
`.env` local. O ganho concreto: Argon2 no custo mínimo, o que mantém a suíte de serviço na casa dos
milissegundos sem enfraquecer o hash de produção.
"""

import os
from pathlib import Path

ENV_TEST = Path(__file__).resolve().parents[1] / ".env.test"

if ENV_TEST.exists():
    for raw_line in ENV_TEST.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())
