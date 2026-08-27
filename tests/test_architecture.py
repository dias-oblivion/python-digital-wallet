"""A regra de dependência como teste executável, não como convenção no README.

Percorre a AST de cada módulo e falha se uma camada importar algo que não deveria. É o que impede
a inversão de dependência de se degradar silenciosamente conforme o projeto cresce.

No layout flat (pacotes na raiz) a comparação é feita pela RAIZ do módulo importado, não por
prefixo de string: `startswith("db")` casaria com `dbm` da stdlib.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# camada -> raízes de módulo PROIBIDAS naquela camada
FORBIDDEN: dict[str, frozenset[str]] = {
    # entidades: só stdlib. Nem outra camada, nem biblioteca de terceiros.
    "models": frozenset(
        {
            "core",
            "ports",
            "services",
            "db",
            "api",
            "fastapi",
            "starlette",
            "pydantic",
            "asyncpg",
            "httpx",
            "jwt",
            "argon2",
            "structlog",
        }
    ),
    # contratos: conhecem apenas entidades
    "ports": frozenset(
        {"services", "db", "api", "core", "fastapi", "starlette", "asyncpg", "httpx"}
    ),
    # regras: models + ports + core (puro). Nunca infraestrutura nem framework web.
    "services": frozenset({"db", "api", "fastapi", "starlette", "pydantic", "asyncpg", "httpx"}),
    # adapters de saída não conhecem a borda de entrada nem as regras
    "db": frozenset({"api", "services", "fastapi", "starlette"}),
}

# as migrations vivem em db/ mas não são a camada db: usam alembic/sqlalchemy por natureza
EXCLUDED = ("migrations",)


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(ROOT).with_suffix("").parts)


def _imported_roots(path: Path) -> set[str]:
    """Raiz de cada módulo importado: `db.schemas.user` -> `db`."""
    package = _module_name(path).rsplit(".", 1)[0]
    roots: set[str] = set()

    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # import relativo: resolve para o caminho absoluto
                parts = package.split(".")
                base = ".".join(parts[: len(parts) - (node.level - 1)])
                roots.add(base.split(".")[0])
            elif node.module:
                roots.add(node.module.split(".")[0])

    return roots


def _layer_modules(layer: str) -> list[Path]:
    return sorted(
        path
        for path in (ROOT / layer).rglob("*.py")
        if path.name != "__init__.py"
        and not any(part in EXCLUDED for part in path.relative_to(ROOT).parts)
    )


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_camada_nao_importa_o_que_nao_deve(layer: str) -> None:
    forbidden = FORBIDDEN[layer]
    violations = [
        f"{_module_name(path)} importa {root}"
        for path in _layer_modules(layer)
        for root in sorted(_imported_roots(path) & forbidden)
    ]

    assert not violations, "violações da regra de dependência:\n" + "\n".join(violations)


def test_routers_nao_conhecem_o_banco() -> None:
    """O router fala com o service; quem escolhe a implementação é só o api/wiring.py."""
    proibido = frozenset({"db", "asyncpg"})
    violations = [
        f"{_module_name(path)} importa {root}"
        for path in _layer_modules("api/routers")
        for root in sorted(_imported_roots(path) & proibido)
    ]

    assert not violations, "\n".join(violations)


def test_todas_as_camadas_existem() -> None:
    """Falha se um diretório for renomeado sem atualizar as regras acima."""
    for layer in FORBIDDEN:
        assert (ROOT / layer).is_dir(), f"camada ausente: {layer}"
