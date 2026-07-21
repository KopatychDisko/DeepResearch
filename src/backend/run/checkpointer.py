"""LangGraph checkpointer setup and compiled research graph context."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

from agents.configuration import Configuration
from agents.graph.checkpoint_serde import create_checkpoint_serde
from agents.graph.pipeline import build_research_graph
from backend.runtime_requirements import ensure_checkpointer_directory


@contextmanager
def sqlite_checkpointer(database_path: str) -> Iterator[SqliteSaver]:
    """Open a WAL-mode SQLite checkpointer and tear it down on exit."""
    connection = sqlite3.connect(database_path, check_same_thread=False, timeout=30.0)
    connection.execute("PRAGMA journal_mode=WAL")
    checkpointer = SqliteSaver(connection, serde=create_checkpoint_serde())
    checkpointer.setup()
    try:
        yield checkpointer
    finally:
        connection.close()


@contextmanager
def compiled_research_graph(settings: Configuration) -> Iterator[object]:
    """Compile the research graph with a SQLite checkpointer for one operation."""
    ensure_checkpointer_directory(settings.sqlite_checkpointer_path)
    graph: StateGraph = build_research_graph()
    with sqlite_checkpointer(settings.sqlite_checkpointer_path) as checkpointer:
        yield graph.compile(checkpointer=checkpointer)
