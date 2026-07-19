from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from agents.graph_state import (
    ResearchRunState,
    dump_company_identity,
    dump_run_request,
)
from agents.models import (
    CompanyIdentity,
    ResponseLanguage,
    RunRequest,
    ToolObservation,
    ToolObservationStatus,
)
from agents.supervisor.node import supervisor_step, supervisor_tools_step


def _minimal_state(
    *,
    iteration_count: int,
    finished: bool,
    conversation_history: list[AIMessage | ToolMessage],
    extra: dict[str, Any] | None,
) -> ResearchRunState:
    request = RunRequest(company_name="Acme", company_url=None, company_description=None)
    identity = CompanyIdentity(
        query_name="Acme",
        canonical_name="Acme",
        normalized_name="acme",
        company_url=None,
        profile_summary=None,
        user_description=None,
    )
    state: ResearchRunState = {
        "run_id": str(uuid4()),
        "phase": "supervisor",
        "status": "running",
        "error_message": None,
        "request": dump_run_request(request),
        "identity": dump_company_identity(identity),
        "findings": [],
        "events": [],
        "timeline": {"events": [], "conflicts": []},
        "verdict": {},
        "identity_candidates": [],
        "completed_sources": [],
        "conversation_history": conversation_history,
        "iteration_count": iteration_count,
        "finished": finished,
    }
    if extra is not None:
        state.update(extra)  # type: ignore[typeddict-item]
    return state


def _config_with_iterations(max_tool_iterations: int) -> RunnableConfig:
    return RunnableConfig(configurable={"max_tool_iterations": max_tool_iterations})


def test_max_tool_iterations_budget_stop_reason() -> None:
    state = _minimal_state(
        iteration_count=5,
        finished=False,
        conversation_history=[],
        extra=None,
    )
    result = supervisor_step(state=state, config=_config_with_iterations(5))
    assert result.goto == "structure_events"
    assert result.update is not None
    assert result.update.get("budget_stop_reason") == "max_tool_iterations"


def test_wall_clock_budget_stop_reason() -> None:
    from agents.configuration import Configuration

    assert "max_run_wall_clock_seconds" in Configuration.model_fields
    state = _minimal_state(
        iteration_count=0,
        finished=False,
        conversation_history=[],
        extra={"budget_deadline_unix": 0.0, "estimated_tokens_used": 0, "budget_stop_reason": None},
    )
    result = supervisor_step(
        state=state,
        config=RunnableConfig(
            configurable={
                "max_tool_iterations": 8,
                "max_run_wall_clock_seconds": 600,
                "max_estimated_run_tokens": 100000,
            }
        ),
    )
    assert result.goto == "structure_events"
    assert result.update is not None
    assert result.update.get("budget_stop_reason") == "wall_clock"


def test_soft_token_budget_stop_reason() -> None:
    from agents.configuration import Configuration

    assert "max_estimated_run_tokens" in Configuration.model_fields
    state = _minimal_state(
        iteration_count=0,
        finished=False,
        conversation_history=[],
        extra={
            "budget_deadline_unix": 9_999_999_999.0,
            "estimated_tokens_used": 100000,
            "budget_stop_reason": None,
        },
    )
    result = supervisor_step(
        state=state,
        config=RunnableConfig(
            configurable={
                "max_tool_iterations": 8,
                "max_run_wall_clock_seconds": 600,
                "max_estimated_run_tokens": 100000,
            }
        ),
    )
    assert result.goto == "structure_events"
    assert result.update is not None
    assert result.update.get("budget_stop_reason") == "soft_token_budget"


def test_unknown_tool_denied_observation() -> None:
    ai_message = AIMessage(
        content="",
        tool_calls=[{"name": "unknown_xyz", "args": {}, "id": "call-unknown-1", "type": "tool_call"}],
    )
    state = _minimal_state(
        iteration_count=1,
        finished=False,
        conversation_history=[ai_message],
        extra=None,
    )
    result = supervisor_tools_step(state=state, config=_config_with_iterations(5))
    assert result.update is not None
    history = result.update["conversation_history"]
    tool_messages = [message for message in history if isinstance(message, ToolMessage)]
    assert len(tool_messages) == 1
    payload = json.loads(str(tool_messages[0].content))
    observation = ToolObservation.model_validate(payload)
    assert observation.status == ToolObservationStatus.DENIED
    assert observation.tool == "unknown_xyz"


def test_source_tool_error_observation_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_source_error(
        tool_name: str,
        identity: object,
        settings: object,
        response_language: object,
    ) -> tuple[object, list[object]]:
        raise RuntimeError("source failed after retries")

    monkeypatch.setattr(
        "agents.supervisor.node._execute_source_tool",
        _raise_source_error,
    )
    ai_message = AIMessage(
        content="",
        tool_calls=[{"name": "search_news", "args": {}, "id": "call-news-1", "type": "tool_call"}],
    )
    state = _minimal_state(
        iteration_count=1,
        finished=False,
        conversation_history=[ai_message],
        extra=None,
    )
    result = supervisor_tools_step(state=state, config=_config_with_iterations(5))
    assert result.goto == "supervisor"
    assert result.update is not None
    history = result.update["conversation_history"]
    tool_messages = [message for message in history if isinstance(message, ToolMessage)]
    assert len(tool_messages) == 1
    payload = json.loads(str(tool_messages[0].content))
    observation = ToolObservation.model_validate(payload)
    assert observation.status == ToolObservationStatus.ERROR
    assert observation.tool == "search_news"
    assert observation.error_code == "RuntimeError"


def test_search_success_observation_omits_finding_body(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.models import RawFinding, RetrievalMetadata, SourceType, utc_now
    from pydantic import AnyHttpUrl

    finding = RawFinding(
        source_type=SourceType.NEWS,
        source_url=AnyHttpUrl("https://example.com/article"),
        title="Secret title",
        snippet="Secret snippet",
        metadata=RetrievalMetadata(fetched_at=utc_now(), source_label="news", note="test"),
    )

    def _fake_source(
        tool_name: str,
        identity: object,
        settings: object,
        response_language: object,
    ) -> tuple[SourceType, list[RawFinding]]:
        return SourceType.NEWS, [finding]

    monkeypatch.setattr("agents.supervisor.node._execute_source_tool", _fake_source)
    ai_message = AIMessage(
        content="",
        tool_calls=[{"name": "search_news", "args": {}, "id": "call-news-2", "type": "tool_call"}],
    )
    state = _minimal_state(
        iteration_count=1,
        finished=False,
        conversation_history=[ai_message],
        extra=None,
    )
    result = supervisor_tools_step(state=state, config=_config_with_iterations(5))
    assert result.update is not None
    history = result.update["conversation_history"]
    tool_messages = [message for message in history if isinstance(message, ToolMessage)]
    assert len(tool_messages) == 1
    payload = json.loads(str(tool_messages[0].content))
    assert "title" not in payload
    assert "source_url" not in payload
    assert "snippet" not in payload
    observation = ToolObservation.model_validate(payload)
    assert observation.status == ToolObservationStatus.OK
    assert observation.tool == "search_news"
    assert observation.counts is not None
    assert observation.source == "news"
