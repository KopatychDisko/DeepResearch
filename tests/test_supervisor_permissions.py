from __future__ import annotations

from agents.supervisor.permissions import RiskClass, authorize_tool


def test_authorize_search_news_allowed_external_read() -> None:
    result = authorize_tool("search_news")
    assert result.allowed is True
    assert result.risk_class == RiskClass.EXTERNAL_READ
    assert result.reason == "allow"


def test_authorize_search_reviews_allowed_external_read() -> None:
    result = authorize_tool("search_reviews")
    assert result.allowed is True
    assert result.risk_class == RiskClass.EXTERNAL_READ
    assert result.reason == "allow"


def test_authorize_search_hh_allowed_external_read() -> None:
    result = authorize_tool("search_hh")
    assert result.allowed is True
    assert result.risk_class == RiskClass.EXTERNAL_READ
    assert result.reason == "allow"


def test_authorize_think_allowed_read() -> None:
    result = authorize_tool("think")
    assert result.allowed is True
    assert result.risk_class == RiskClass.READ
    assert result.reason == "allow"


def test_authorize_finish_research_allowed_control() -> None:
    result = authorize_tool("finish_research")
    assert result.allowed is True
    assert result.risk_class == RiskClass.CONTROL
    assert result.reason == "allow"


def test_authorize_unknown_tool_denied_without_raise() -> None:
    result = authorize_tool("unknown_xyz")
    assert result.allowed is False
    assert result.risk_class is None
    assert result.reason == "unknown_tool"


def test_authorize_search_news_allowed_when_source_already_completed() -> None:
    """D-12: pure matrix has no completed_sources argument; duplicate search remains allowed."""
    result = authorize_tool("search_news")
    assert result.allowed is True
    assert result.risk_class == RiskClass.EXTERNAL_READ
