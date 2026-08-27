# Instruções do projeto

## Commits

**NUNCA** adicionar `Co-Authored-By: Claude` (ou qualquer variação de coautoria/atribuição a
Claude, Anthropic ou Claude Code) nas mensagens de commit. A Anthropic já aplica marca d'água no
que é gerado pelo Claude Code; não precisa poluir o histórico do git com isso.

Mensagem de commit: imperativo, em português, sem rodapé de atribuição.

## Arquitetura — a regra de dependência

Camadas técnicas com inversão de dependência. Toda seta aponta de fora para dentro:

```
  api/routers ──┐
                ├──►  services  ──►  ports  ◄────── db/repositories
  api/wiring ───┘         │
                          ▼
                       models  +  core (puro)
```

| pacote | pode importar | nunca importa |
|---|---|---|
| `models/` | stdlib | nada do projeto, nada de terceiros |
| `ports/` | `models/` | `services`, `db`, `api`, `core` |
| `services/` | `models/`, `ports/`, `core/` | `fastapi`, `pydantic`, `asyncpg`, `db/`, `api/` |
| `db/` | `models/`, `ports/`, `core/` | `api/`, `services/`, `fastapi` |
| `api/` | tudo — é o wiring | — |

`tests/test_architecture.py` valida isso na AST. Se ele quebrar, **corrija o import, não o teste**.

Pontos que não devem ser "simplificados" por engano:

- `api/wiring.py` é o composition root: o único lugar que amarra port a implementação. A
  assinatura do provider declara o **port**, o corpo instancia a **impl** — é isso que faz o mypy
  verificar a conformidade do `Protocol`.
- Implementações de port **não herdam** do `Protocol` (structural typing).
- `core/errors.py` não conhece HTTP; o mapeamento para status code fica em `api/handlers.py`.
- Nenhum `asyncpg.Record` sai do pacote `db/` — a conversão para entidade é em `db/schemas/`.

## Banco

- asyncpg com **SQL nativo**, sem ORM. Não introduzir SQLAlchemy como camada de acesso a dados.
- Migrations do Alembic são escritas **à mão**: sem modelos, `--autogenerate` não funciona.
- Escrita usa `get_tx_conn` (transação por request); leitura usa `get_conn`.

## Comandos

```bash
make test-unit    # loop rápido: sem Docker, sem banco
make test         # suíte completa (Testcontainers sobe Postgres)
make lint         # ruff check + format --check
make typecheck    # mypy --strict
make check        # tudo que o CI roda
make up           # Postgres + API no Docker
```

Antes de considerar qualquer mudança pronta: `make check` verde. Novo comportamento precisa de
teste unitário com fake; SQL novo precisa de teste de integração.
