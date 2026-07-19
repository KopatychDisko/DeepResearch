"""Filesystem path helpers for the project root and frontend build output."""

from pathlib import Path


def project_root() -> Path:
    """Return the repository root two levels above this backend package."""
    return Path(__file__).resolve().parents[2]


def frontend_directory() -> Path:
    """Return the path to the Vite frontend source tree under src/frontend."""
    return project_root() / "src" / "frontend"


def frontend_dist_directory() -> Path:
    """Return the path to the frontend production build under frontend/dist."""
    return frontend_directory() / "dist"
