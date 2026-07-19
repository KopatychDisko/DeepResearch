from __future__ import annotations

import ast
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_AGENTS = PROJECT_ROOT / "src" / "agents"
SRC_BACKEND = PROJECT_ROOT / "src" / "backend"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"

REQUIRED_SUBAGENT_DIRS: tuple[str, ...] = (
    "identity",
    "supervisor",
    "sources",
    "structure_events",
    "merge",
    "verdict",
)

SOURCES_MODULES: tuple[str, ...] = (
    "common.py",
    "news.py",
    "reviews.py",
    "hh.py",
)


def test_agents_and_backend_packages_importable() -> None:
    import agents
    import backend

    assert agents.__file__ is not None
    assert backend.__file__ is not None
    assert Path(agents.__file__).resolve().is_relative_to(SRC_AGENTS.resolve())
    assert Path(backend.__file__).resolve().is_relative_to(SRC_BACKEND.resolve())


def test_subagent_folders_exist_under_src_agents() -> None:
    assert SRC_AGENTS.is_dir()
    for name in REQUIRED_SUBAGENT_DIRS:
        subpackage = SRC_AGENTS / name
        assert subpackage.is_dir(), f"missing subagent package dir: {subpackage}"
        assert (subpackage / "__init__.py").is_file(), f"missing {name}/__init__.py"


def test_sources_modules_exist() -> None:
    sources_dir = SRC_AGENTS / "sources"
    assert sources_dir.is_dir(), f"missing sources package dir: {sources_dir}"
    for name in SOURCES_MODULES:
        module_path = sources_dir / name
        assert module_path.is_file(), f"missing sources module: {module_path}"


def test_pipeline_assembler_exists() -> None:
    pipeline_path = SRC_AGENTS / "pipeline.py"
    assert pipeline_path.is_file(), f"missing pipeline assembler: {pipeline_path}"


def test_hatch_packages_are_agents_and_backend_only() -> None:
    raw = PYPROJECT.read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    packages = data["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    assert packages == ["src/agents", "src/backend"]
    src_root = PROJECT_ROOT / "src"
    python_package_dirs = {
        path.name
        for path in src_root.iterdir()
        if path.is_dir() and (path / "__init__.py").is_file()
    }
    assert python_package_dirs == {"agents", "backend"}


def _python_files_under(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _module_imports_backend(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "backend" or alias.name.startswith("backend."):
                    return True
        if isinstance(node, ast.ImportFrom):
            if node.module is not None and (
                node.module == "backend" or node.module.startswith("backend.")
            ):
                return True
    return False


def test_agents_tree_does_not_import_backend() -> None:
    offenders: list[str] = []
    for path in _python_files_under(SRC_AGENTS):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        if _module_imports_backend(tree):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == [], f"agents must not import backend: {offenders}"
