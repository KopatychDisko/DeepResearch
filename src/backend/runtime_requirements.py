"""Runtime preflight checks for Tavily credentials and checkpointer directories."""

from __future__ import annotations

import os


def require_tavily_api_key() -> None:
    """Raise RuntimeError when TAVILY_API_KEY is missing from the environment."""
    if os.environ.get("TAVILY_API_KEY") is None:
        raise RuntimeError("Missing Tavily credentials: set TAVILY_API_KEY.")


def ensure_checkpointer_directory(database_path: str) -> None:
    """Create the parent directory for the SQLite checkpointer path if needed."""
    directory: str = os.path.dirname(database_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
