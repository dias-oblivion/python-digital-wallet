# ---------------------------------------------------------------- builder
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# só os manifestos primeiro: a camada de dependências só invalida quando eles mudam
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# depois o código — mudar um .py não refaz a resolução de dependências
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------------------------------------------------------------- runtime
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --create-home app

WORKDIR /app

# só o virtualenv atravessa: o uv e o cache de build ficam para trás
COPY --from=builder --chown=app:app /app/.venv ./.venv
COPY --chown=app:app src ./src
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app alembic.ini ./

USER app
EXPOSE 8000

CMD ["uvicorn", "wallet.main:app", "--host", "0.0.0.0", "--port", "8000"]
