# python-digital-wallet

API REST de carteira digital, escrita para estudar e praticar. O foco não é a quantidade de
endpoints: é a **arquitetura em camadas com inversão de dependência** e SQL nativo, sem ORM.

## Stack

| camada | escolha |
|---|---|
| Web / validação | FastAPI, Pydantic |
| Banco | PostgreSQL, **asyncpg** (SQL nativo, sem ORM) |
| Migrations | Alembic (escritas à mão — sem `--autogenerate`) |
| Ambiente | uv, Docker + Docker Compose |
| Qualidade | Ruff, mypy `--strict` |
| Segurança | PyJWT (HS256), Argon2 |
| Testes | pytest, httpx, Testcontainers |
| Observabilidade | structlog (JSON) |

## A regra que sustenta o projeto

```
        ENTRADA                  NÚCLEO                   SAÍDA
  api/routers ──┐
                ├──►  services  ──►  ports  ◄────── db/repositories
  api/wiring ───┘         │
  (composition root)      ▼
                       models  +  core (puro)
```

Toda seta aponta de fora para dentro. O núcleo (`models`, `ports`, `services`) não sabe que existe
Postgres nem HTTP.

| pacote | pode importar | nunca importa |
|---|---|---|
| `models/` | stdlib | nada do projeto |
| `ports/` | `models/` | `services`, `db`, `api`, `core` |
| `services/` | `models/`, `ports/`, `core/` | `fastapi`, `pydantic`, `asyncpg`, `db/`, `api/` |
| `db/` | `models/`, `ports/`, `core/` | `api/`, `services/`, `fastapi` |
| `api/` | tudo — é o wiring | — |

Isso **não** é só convenção de README: [`tests/test_architecture.py`](tests/test_architecture.py)
percorre a AST de cada módulo e falha se alguma camada importar o que não deve (comparando a raiz
do módulo, para `dbm` da stdlib não ser confundido com `db/`). Durante a
construção deste projeto o teste já pegou uma violação real (o router de health importava
`db/pool.py`).

### Como a inversão funciona na prática

O contrato fala só de entidades ([`ports/repositories.py`](ports/repositories.py)):

```python
class UserRepository(Protocol):
    async def by_email(self, email: str) -> User | None: ...
    async def add(self, user: User) -> None: ...
```

O service recebe o contrato pelo construtor e nunca sabe quem chegou
([`services/auth.py`](services/auth.py)):

```python
class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users
```

O **composition root** ([`api/wiring.py`](api/wiring.py)) é o único lugar que conhece a
implementação concreta — a assinatura declara o port, o corpo instancia a impl:

```python
def get_user_repository(conn: ConnDep) -> UserRepository:  # ← port
    return PgUserRepository(conn)  # ← impl
```

`PgUserRepository` **não herda** de `UserRepository`: `Protocol` é structural typing, e o
`mypy --strict` verifica a conformidade exatamente nessa linha.

O resultado é a suíte de regra de negócio rodando sem Docker, sem banco e sem um único mock:

```python
svc = AuthService(users=InMemoryUserRepository())
with pytest.raises(ConflictError):
    await svc.register(email="ja@existe.com", password=..., full_name=...)
```

## Estrutura

```
main.py                  # Main Component: lifespan, middlewares, handlers
core/                    # infra transversal e PURA (sem I/O, sem framework)
├── config.py            # Settings (pydantic-settings)
├── errors.py            # AppError e subclasses — sem noção de HTTP
├── logging.py           # structlog JSON
└── security.py          # Argon2 + PyJWT
models/                  # entidades: @dataclass(frozen=True), só stdlib
ports/                   # CONTRATOS (Protocol)
services/                # REGRAS de negócio
db/
├── connection.py        # aliases DbConnection / DbPool
├── pool.py              # ciclo de vida do pool asyncpg
├── migrations/          # Alembic (env.py + versions/)
├── schemas/             # forma da LINHA: colunas + Record -> entidade
└── repositories/        # SQL nativo, implementa os ports
api/
├── wiring.py            # COMPOSITION ROOT: port -> impl
├── router.py            # agrega em /api/v1
├── handlers.py          # AppError -> status HTTP
├── middleware.py        # request_id + log por request
├── schemas/             # Pydantic da borda
└── routers/             # auth, users, health
tests/
├── test_architecture.py # a regra de dependência como teste
├── fakes/               # implementam os mesmos Protocols
├── unit/                # zero I/O, sem Docker
└── integration/         # Postgres real via Testcontainers
```

Layout **flat**: os pacotes ficam na raiz, sem um pacote guarda-chuva. Consequência: o projeto não
é instalável (`[tool.uv] package = false`) e os imports resolvem pelo diretório de trabalho —
`pythonpath` no pytest, `prepend_sys_path` no Alembic e `PYTHONPATH=/app` no Docker. Por isso a
API sobe com `python -m uvicorn main:app`, e não `uvicorn main:app`: o `-m` garante o cwd no
`sys.path`.

## Rodando

Pré-requisitos: Python 3.12, [uv](https://docs.astral.sh/uv/) e Docker.

```bash
uv sync                     # cria o .venv a partir do uv.lock
cp .env.example .env        # ajuste JWT_SECRET: openssl rand -hex 32

make test-unit              # suíte rápida: NÃO precisa de Docker nem de banco
make db-up && make migrate  # Postgres no Docker + alembic upgrade head
make run                    # API em http://localhost:8000/docs
make test                   # suíte completa (Testcontainers sobe outro Postgres)
```

Tudo no Docker, incluindo a API com reload:

```bash
make up
```

`make help` lista todos os alvos.

### Smoke manual

```bash
curl -sX POST localhost:8000/api/v1/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"ana@example.com","password":"senha-forte-123","full_name":"Ana Souza"}'

TOKEN=$(curl -sX POST localhost:8000/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"ana@example.com","password":"senha-forte-123"}' | jq -r .access_token)

curl -s localhost:8000/api/v1/users/me -H "authorization: Bearer $TOKEN"
```

## Endpoints

| método | rota | descrição |
|---|---|---|
| POST | `/api/v1/auth/register` | cria usuário (Argon2 no hash da senha) |
| POST | `/api/v1/auth/login` | devolve access + refresh token |
| POST | `/api/v1/auth/refresh` | troca refresh por um par novo |
| GET | `/api/v1/users/me` | usuário do token (Bearer) |
| GET | `/health/live` | processo de pé, não toca no banco |
| GET | `/health/ready` | pronto para tráfego: exige o banco |

Todo erro sai no mesmo envelope, inclusive os de validação:

```json
{
  "error": { "code": "conflict", "message": "e-mail já cadastrado", "details": {"field": "email"} },
  "request_id": "0b9c…"
}
```

## Decisões e trade-offs

**Sem ORM.** `asyncpg` fala o protocolo Postgres direto. Consequências: as migrations são escritas à
mão (não há metadata para o `--autogenerate` comparar) e `db/schemas/` é o único lugar que conhece
nomes de coluna.

**SQLite nos testes foi descartado.** `asyncpg` só fala Postgres, e o SQL que vale praticar
(`ON CONFLICT`, `RETURNING`, `uuid`, `timestamptz`) não roda em SQLite. Teste rápido sem banco vem
dos *fakes*; fidelidade vem do Postgres real. Trocar isso exigiria SQLAlchemy Core e SQL portable —
o oposto do objetivo.

**Argon2 parametrizado por config.** O hash é lento de propósito. Em vez de abstrair um
`PasswordHasher`, `.env.test` baixa o custo ao mínimo: a suíte roda em milissegundos e produção
segue forte.

**Transação por request, não Unit of Work.** `get_tx_conn` abre a transação na borda: commit no fim
do request, rollback em exceção. Cobre também a transferência atômica futura, já que débito, crédito
e ledger acontecem no mesmo request.

**Sem abstração de relógio.** Testar token expirado usa TTL negativo
(`create_access_token(uid, ttl=timedelta(seconds=-1))`).

**Refresh token stateless.** Não há tabela de tokens: revogar exigiria persistir o `jti`. É a
evolução natural quando logout de verdade entrar no escopo.

**`asyncpg.Pool` é genérico só nos stubs.** Em runtime `asyncpg.Pool[Record]` levanta
`TypeError: not subscriptable`. Daí o bloco `TYPE_CHECKING` em
[`db/connection.py`](db/connection.py): mypy vê os parâmetros de tipo, o interpretador vê
a classe crua.

## Próximos passos

`wallets` (saldo, moeda) e `transactions` (depósito, saque, transferência com ledger de dupla
entrada e idempotência). Cada domínio novo entra sempre pelo mesmo caminho:

1. entidade em `models/`
2. contrato em `ports/repositories.py`
3. regra em `services/` + fake em `tests/fakes/` + teste unitário
4. SQL em `db/schemas/` e `db/repositories/` + migration
5. borda em `api/schemas/` e `api/routers/`
6. uma linha em `api/wiring.py`

Uma integração com API externa (pagamento, cotação, e-mail) segue exatamente a mesma receita:
contrato em `ports/gateways.py`, adapter httpx em `gateways/`, fake nos testes, escolha da
implementação no wiring.
