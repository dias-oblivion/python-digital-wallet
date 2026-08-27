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

# o projeto não é um pacote instalável, então o sync resolve apenas as dependências

# ---------------------------------------------------------------- runtime
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app

RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --create-home app

WORKDIR /app

# só o virtualenv atravessa: o uv e o cache de build ficam para trás
COPY --from=builder --chown=app:app /app/.venv ./.venv
COPY --chown=app:app api ./api
COPY --chown=app:app core ./core
COPY --chown=app:app db ./db
COPY --chown=app:app models ./models
COPY --chown=app:app ports ./ports
COPY --chown=app:app services ./services
COPY --chown=app:app main.py alembic.ini ./

USER app
EXPOSE 8000

# python -m garante o cwd no sys.path — o projeto não está instalado no venv
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
