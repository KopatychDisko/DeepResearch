"""LangChain tool schemas the supervisor model may call during research."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def search_news(query: str) -> str:
    """Search company news in open web sources."""
    return f"search_news requested for query={query}"


@tool
def search_reviews(query: str) -> str:
    """Search employee reviews and reputation signals."""
    return f"search_reviews requested for query={query}"


@tool
def search_hh(query: str) -> str:
    """Search hiring footprint and job posting signals on hh.ru."""
    return f"search_hh requested for query={query}"


@tool
def think(reflection: str) -> str:
    """Think through gaps before choosing next action."""
    return reflection


@tool
def finish_research(reason: str) -> str:
    """Finish research when enough grounded findings are collected."""
    return reason
