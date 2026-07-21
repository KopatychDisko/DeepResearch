"""Supervisor research loop: budgets, model tool calls, and ToolObservation routing."""

from __future__ import annotations

import time
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from agents.configuration import Configuration
from agents.graph.state import (
    ResearchRunState,
    dump_completed_sources,
    dump_raw_findings,
    load_company_identity,
    load_completed_sources,
    load_raw_findings,
    load_run_request,
)
from agents.llm_service import create_llm_with_tools
from agents.models import (
    CompanyIdentity,
    RawFinding,
    RunPhase,
    SourceType,
    ToolObservation,
    ToolObservationStatus,
)
from agents.prompts import SUPERVISOR_PROMPT
from agents.supervisor.budget import (
    budget_exhausted,
    budget_stop_command,
    resolve_budget_deadline,
    tokens_from_supervisor_turn,
)
from agents.supervisor.permissions import authorize_tool
from agents.supervisor.prompt_context import (
    company_context_text,
    completed_sources_text,
    format_recent_tool_outcomes,
)
from agents.supervisor.tool_runner import execute_source_tool, tool_observation_message
from agents.supervisor.tools import (
    finish_research,
    search_hh,
    search_news,
    search_reviews,
    think,
)

_RECENT_TOOL_OUTCOMES_LIMIT: int = 3


def _phase_update(phase: RunPhase) -> dict[str, str]:
    return {"phase": phase.value}


def supervisor_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["supervisor_tools", "structure_events"]]:
    """Run one supervisor model turn or stop the loop when a budget is exhausted."""
    settings: Configuration = Configuration.from_runnable_config(config)

    if state["finished"]:
        return Command(goto="structure_events")

    deadline, budget_state_update = resolve_budget_deadline(state=state, settings=settings)
    stop_reason: str | None = budget_exhausted(
        state=state,
        settings=settings,
        deadline=deadline,
    )
    if stop_reason is not None:
        return budget_stop_command(
            budget_stop_reason=stop_reason,
            extra_update=budget_state_update,
        )

    identity: CompanyIdentity = load_company_identity(state["identity"])
    request = load_run_request(state["request"])
    completed_sources: list[SourceType] = load_completed_sources(state["completed_sources"])
    findings: list[RawFinding] = load_raw_findings(state["findings"])
    recent_tool_outcomes: str = format_recent_tool_outcomes(
        conversation_history=state["conversation_history"],
        max_outcomes=_RECENT_TOOL_OUTCOMES_LIMIT,
    )

    tools = [search_news, search_reviews, search_hh, think, finish_research]
    tools_model = create_llm_with_tools(tools=tools, config=config)

    system_prompt_text: str = SUPERVISOR_PROMPT.format(
        company_name=identity.canonical_name,
        completed_sources=completed_sources_text(completed_sources),
        findings_count=len(findings),
        company_context=company_context_text(
            identity=identity,
            language=request.response_language,
        ),
        recent_tool_outcomes=recent_tool_outcomes,
    )
    system_message = SystemMessage(content=system_prompt_text)
    user_message_text: str = "Choose the next research tool call."
    user_message = HumanMessage(content=user_message_text)

    response = tools_model.invoke([system_message, user_message])
    if not isinstance(response, AIMessage):
        raise TypeError("Supervisor model returned unexpected response type")

    turn_tokens: int = tokens_from_supervisor_turn(
        response=response,
        prompt_texts=[system_prompt_text, user_message_text],
    )
    updated_history: list[AIMessage | ToolMessage] = [*state["conversation_history"], response]
    estimated_tokens_used: int = int(state.get("estimated_tokens_used") or 0)

    return Command(
        goto="supervisor_tools",
        update={
            **budget_state_update,
            "conversation_history": updated_history,
            "iteration_count": state["iteration_count"] + 1,
            "estimated_tokens_used": estimated_tokens_used + turn_tokens,
            **_phase_update(RunPhase.SUPERVISOR),
        },
    )


def supervisor_tools_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["supervisor", "structure_events"]]:
    """Authorize and execute tool calls, then loop back or hand off to structure_events."""
    settings: Configuration = Configuration.from_runnable_config(config)

    deadline: float | None = state.get("budget_deadline_unix")
    if deadline is not None and time.time() >= float(deadline):
        return budget_stop_command(
            budget_stop_reason="wall_clock",
            extra_update={},
        )

    if not state["conversation_history"]:
        return Command(goto="structure_events")

    last_message = state["conversation_history"][-1]
    if isinstance(last_message, ToolMessage):
        return Command(goto="supervisor")
    if not isinstance(last_message, AIMessage):
        raise TypeError("Conversation history tail must be AIMessage or ToolMessage")

    tool_calls = last_message.tool_calls
    if not tool_calls:
        return Command(goto="structure_events")

    identity: CompanyIdentity = load_company_identity(state["identity"])
    request = load_run_request(state["request"])
    updated_findings: list[RawFinding] = load_raw_findings(state["findings"])
    updated_sources: list[SourceType] = load_completed_sources(state["completed_sources"])
    updated_history: list[AIMessage | ToolMessage] = [*state["conversation_history"]]
    finish_requested: bool = state["finished"]

    for tool_call in tool_calls:
        tool_name: str = str(tool_call.get("name"))
        tool_id: str = str(tool_call.get("id"))
        tool_args_value = tool_call.get("args", {})
        if not isinstance(tool_args_value, dict):
            tool_args_value = {}

        authorization = authorize_tool(tool_name)
        if not authorization.allowed:
            updated_history.append(
                tool_observation_message(
                    observation=ToolObservation(
                        status=ToolObservationStatus.DENIED,
                        tool=tool_name,
                        summary=f"Tool {tool_name} is not permitted",
                        error_code=authorization.reason,
                        error_message=f"Tool {tool_name} is not in the permission matrix",
                    ),
                    tool_call_id=tool_id,
                    tool_name=tool_name,
                )
            )
            continue

        if tool_name in {"search_news", "search_reviews", "search_hh"}:
            try:
                source_type, source_findings = execute_source_tool(
                    tool_name=tool_name,
                    identity=identity,
                    settings=settings,
                    response_language=request.response_language,
                )
            except Exception as error:
                updated_history.append(
                    tool_observation_message(
                        observation=ToolObservation(
                            status=ToolObservationStatus.ERROR,
                            tool=tool_name,
                            summary="Source search failed after retries",
                            error_code=type(error).__name__,
                            error_message=str(error),
                        ),
                        tool_call_id=tool_id,
                        tool_name=tool_name,
                    )
                )
                continue

            updated_findings.extend(source_findings)
            if source_type not in updated_sources:
                updated_sources.append(source_type)
            updated_history.append(
                tool_observation_message(
                    observation=ToolObservation(
                        status=ToolObservationStatus.OK,
                        tool=tool_name,
                        summary=f"Collected findings from {source_type.value}",
                        counts={"findings": len(source_findings)},
                        source=source_type.value,
                    ),
                    tool_call_id=tool_id,
                    tool_name=tool_name,
                )
            )
            continue

        if tool_name == "think":
            reflection: str = str(tool_args_value.get("reflection", ""))
            updated_history.append(
                tool_observation_message(
                    observation=ToolObservation(
                        status=ToolObservationStatus.OK,
                        tool=tool_name,
                        summary=reflection,
                    ),
                    tool_call_id=tool_id,
                    tool_name=tool_name,
                )
            )
            continue

        if tool_name == "finish_research":
            finish_requested = True
            reason: str = str(tool_args_value.get("reason", "No reason provided"))
            updated_history.append(
                tool_observation_message(
                    observation=ToolObservation(
                        status=ToolObservationStatus.OK,
                        tool=tool_name,
                        summary=reason,
                    ),
                    tool_call_id=tool_id,
                    tool_name=tool_name,
                )
            )
            continue

        updated_history.append(
            tool_observation_message(
                observation=ToolObservation(
                    status=ToolObservationStatus.DENIED,
                    tool=tool_name,
                    summary=f"Tool {tool_name} is not permitted",
                    error_code="unknown_tool",
                    error_message=f"Tool {tool_name} is not in the permission matrix",
                ),
                tool_call_id=tool_id,
                tool_name=tool_name,
            )
        )

    next_node: Literal["supervisor", "structure_events"] = "supervisor"
    if finish_requested:
        next_node = "structure_events"

    return Command(
        goto=next_node,
        update={
            "findings": dump_raw_findings(updated_findings),
            "completed_sources": dump_completed_sources(updated_sources),
            "conversation_history": updated_history,
            "finished": finish_requested,
        },
    )
