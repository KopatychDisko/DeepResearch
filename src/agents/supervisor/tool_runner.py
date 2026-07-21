"""Supervisor tool authorization, execution, and observation messages."""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from agents.configuration import Configuration
from agents.models import (
    CompanyIdentity,
    RawFinding,
    ResponseLanguage,
    SourceType,
    ToolObservation,
)
from agents.observability import trace_source_research
from agents.sources.hh import fetch_hh
from agents.sources.news import fetch_news
from agents.sources.reviews import fetch_reviews


def tool_observation_message(
    observation: ToolObservation,
    tool_call_id: str,
    tool_name: str,
) -> ToolMessage:
    """Serialize a ToolObservation into a LangChain ToolMessage."""
    return ToolMessage(
        content=json.dumps(observation.model_dump(mode="json")),
        tool_call_id=tool_call_id,
        name=tool_name,
    )


def execute_source_tool(
    tool_name: str,
    identity: CompanyIdentity,
    settings: Configuration,
    response_language: ResponseLanguage,
) -> tuple[SourceType, list[RawFinding]]:
    """Run one source search tool and return its source type plus findings."""
    if tool_name == "search_news":
        source_type: SourceType = SourceType.NEWS

        def fetch_action() -> list[RawFinding]:
            return fetch_news(identity=identity, settings=settings)

        findings: list[RawFinding] = trace_source_research(
            source_type=source_type,
            company_name=identity.canonical_name,
            response_language=response_language,
            action=fetch_action,
        )
        return source_type, findings
    if tool_name == "search_reviews":
        source_type = SourceType.REVIEWS

        def fetch_action() -> list[RawFinding]:
            return fetch_reviews(identity=identity, settings=settings)

        findings = trace_source_research(
            source_type=source_type,
            company_name=identity.canonical_name,
            response_language=response_language,
            action=fetch_action,
        )
        return source_type, findings
    if tool_name == "search_hh":
        source_type = SourceType.HH

        def fetch_action() -> list[RawFinding]:
            return fetch_hh(identity=identity, settings=settings)

        findings = trace_source_research(
            source_type=source_type,
            company_name=identity.canonical_name,
            response_language=response_language,
            action=fetch_action,
        )
        return source_type, findings
    raise ValueError(f"Unsupported source tool call: {tool_name}")
