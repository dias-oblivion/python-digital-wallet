.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help install lint fmt typecheck test-unit test check run migrate migration \
        db-up up down down-v logs

help:  ## lista os alvos disponíveis
	@grep -hE '^[a-z][a-z-]*:.*?## ' $(MAKEFILE_LIST) \
	| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## sincroniza o .venv com o uv.lock
	uv sync

lint:  ## ruff check + format --check
	uv run ruff check .
	uv run ruff format --check .

fmt:  ## aplica os fixes do ruff e formata
	uv run ruff check --fix .
	uv run ruff format .

typecheck:  ## mypy --strict
	uv run mypy

test-unit:  ## suíte rápida: sem Docker, sem banco
	uv run pytest tests/unit tests/test_architecture.py

test:  ## suíte completa (Testcontainers sobe um Postgres real)
	uv run pytest

check: lint typecheck test  ## tudo que o CI roda

run:  ## sobe a API local (exige Postgres em pé — use make db-up)
	uv run uvicorn wallet.main:app --reload

migrate:  ## aplica as migrations pendentes
	uv run alembic upgrade head

migration:  ## cria uma revision vazia — make migration m="add wallets"
	uv run alembic revision -m "$(m)"

db-up:  ## sobe apenas o Postgres
	$(COMPOSE) up -d db

up:  ## sobe Postgres + API no Docker
	$(COMPOSE) up --build

down:  ## derruba os containers
	$(COMPOSE) down

down-v:  ## derruba os containers E apaga o volume do banco
	$(COMPOSE) down -v

logs:  ## acompanha o log da API
	$(COMPOSE) logs -f api
