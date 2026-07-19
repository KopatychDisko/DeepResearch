from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Progressive allowlist — Plan 01 harness files; expanded in Plans 02–03.
REQUIRED_DOC_FILES: tuple[str, ...] = (
    "src/agents/supervisor/node.py",
    "src/agents/supervisor/permissions.py",
    "src/agents/supervisor/tools.py",
    "src/agents/pipeline.py",
    "src/agents/models.py",
    "src/agents/configuration.py",
    "src/agents/observability.py",
    "src/agents/graph_state.py",
    "src/agents/prompts.py",
    "src/agents/identity/node.py",
    "src/agents/identity/resolution.py",
    "src/agents/sources/common.py",
    "src/agents/sources/news.py",
    "src/agents/sources/reviews.py",
    "src/agents/sources/hh.py",
)


def _public_defs(tree: ast.AST) -> list[ast.AST]:
    out: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                out.append(node)
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(
                        item, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ) and not item.name.startswith("_"):
                        out.append(item)
    return out


def test_required_modules_have_docstrings() -> None:
    missing: list[str] = []
    for rel in REQUIRED_DOC_FILES:
        path = PROJECT_ROOT / rel
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        if not ast.get_docstring(tree):
            missing.append(f"{rel}:module")
        for node in _public_defs(tree):
            if not ast.get_docstring(node):
                missing.append(f"{rel}:{getattr(node, 'name', '?')}")
    assert missing == [], f"missing docstrings: {missing}"
