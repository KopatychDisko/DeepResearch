from __future__ import annotations

import os


def require_tavily_api_key() -> None:
    if os.environ.get("TAVILY_API_KEY") is None:
        raise RuntimeError("Missing Tavily credentials: set TAVILY_API_KEY.")


def ensure_checkpointer_directory(database_path: str) -> None:
    directory: str = os.path.dirname(database_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
