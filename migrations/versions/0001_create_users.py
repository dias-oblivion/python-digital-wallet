"""create users

Revision ID: 0001
Revises:
Create Date: 2026-08-27

Escrita à mão em SQL nativo: sem modelos SQLAlchemy não há `--autogenerate`.

Duas decisões que valem nota:

- `email` é `text` com um índice único sobre `lower(email)`, em vez do tipo `citext`. Evita
  depender de uma extensão do Postgres e mantém a unicidade case-insensitive. O service
  normaliza o e-mail antes de gravar, e o repositório consulta com `lower(email) = lower($1)`
  para casar com esse índice.
- `id` é gerado na aplicação (`uuid4()` em `User.new`), não pelo banco. Assim a entidade já
  nasce completa e o service não precisa de round-trip para saber o id.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE users (
            id            uuid        PRIMARY KEY,
            email         text        NOT NULL,
            password_hash text        NOT NULL,
            full_name     text        NOT NULL,
            is_active     boolean     NOT NULL DEFAULT true,
            created_at    timestamptz NOT NULL DEFAULT now(),
            updated_at    timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX users_email_lower_key ON users (lower(email))")


def downgrade() -> None:
    op.execute("DROP TABLE users")
