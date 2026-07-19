from __future__ import annotations

from pathlib import Path

from backend.paths import frontend_directory, frontend_dist_directory

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_frontend_directory_resolves_under_src_frontend() -> None:
    frontend_dir = frontend_directory()
    resolved = Path(frontend_dir).resolve()
    expected = (PROJECT_ROOT / "src" / "frontend").resolve()
    assert resolved == expected
    assert resolved.as_posix().endswith("src/frontend")
    assert frontend_directory().is_dir()


def test_frontend_dist_directory_resolves_under_src_frontend_dist() -> None:
    dist_dir = frontend_dist_directory()
    resolved = Path(dist_dir).resolve()
    expected = (PROJECT_ROOT / "src" / "frontend" / "dist").resolve()
    assert resolved == expected
    assert resolved.as_posix().endswith("src/frontend/dist")
