"""A regra de dependência como teste executável, não como convenção no README.

Percorre a AST de cada módulo e falha se uma camada importar algo que não deveria. É o que impede a
inversão de dependência de se degradar silenciosamente conforme o projeto cresce.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
PKG = SRC / "wallet"

# camada -> prefixos de import PROIBIDOS naquela camada
FORBIDDEN: dict[str, tuple[str, ...]] = {
    # entidades: nada do projeto, nenhuma biblioteca de terceiros — só stdlib
    "models": (
        "wallet.",
        "fastapi",
        "starlette",
        "pydantic",
        "asyncpg",
        "httpx",
        "jwt",
        "argon2",
        "structlog",
    ),
    # contratos: só conhecem entidades
    "ports": (
        "wallet.services",
        "wallet.db",
        "wallet.api",
        "wallet.core",
        "fastapi",
        "starlette",
        "asyncpg",
        "httpx",
    ),
    # regras: models + ports + core (puro). Nunca infraestrutura nem framework.
    "services": (
        "wallet.db",
        "wallet.api",
        "fastapi",
        "starlette",
        "pydantic",
        "asyncpg",
        "httpx",
    ),
    # adapters de saída não conhecem a borda de entrada nem as regras
    "db": ("wallet.api", "wallet.services", "fastapi", "starlette"),
}


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(SRC).with_suffix("").parts)


def _imported_modules(path: Path) -> set[str]:
    package = _module_name(path).rsplit(".", 1)[0]
    found: set[str] = set()

    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # import relativo: resolve para o caminho absoluto
                parts = package.split(".")
                base = ".".join(parts[: len(parts) - (node.level - 1)])
                found.add(f"{base}.{node.module}" if node.module else base)
            elif node.module:
                found.add(node.module)

    return found


def _layer_modules(layer: str) -> list[Path]:
    return sorted(p for p in (PKG / layer).rglob("*.py") if p.name != "__init__.py")


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_camada_nao_importa_o_que_nao_deve(layer: str) -> None:
    forbidden = FORBIDDEN[layer]
    violations: list[str] = []

    for module_path in _layer_modules(layer):
        for imported in sorted(_imported_modules(module_path)):
            if imported.startswith(forbidden):
                violations.append(f"{_module_name(module_path)} importa {imported}")

    assert not violations, "violações da regra de dependência:\n" + "\n".join(violations)


def test_routers_nao_conhecem_o_banco() -> None:
    """O router fala com o service; quem escolhe a implementação é só o api/wiring.py."""
    violations = [
        f"{_module_name(path)} importa {imported}"
        for path in _layer_modules("api/routers")
        for imported in sorted(_imported_modules(path))
        if imported.startswith(("wallet.db", "asyncpg"))
    ]
    assert not violations, "\n".join(violations)


def test_todas_as_camadas_existem() -> None:
    """Falha se um diretório for renomeado sem atualizar as regras acima."""
    for layer in FORBIDDEN:
        assert (PKG / layer).is_dir(), f"camada ausente: {layer}"
