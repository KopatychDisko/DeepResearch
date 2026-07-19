from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def frontend_directory() -> Path:
    return project_root() / "src" / "frontend"


def frontend_dist_directory() -> Path:
    return frontend_directory() / "dist"
