from __future__ import annotations

import json
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from agents.configuration import Configuration
from agents.graph_state import (
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
    ResponseLanguage,
    SourceType,
    ToolObservation,
    ToolObservationStatus,
)
from agents.observability import trace_source_research
from agents.prompts import SUPERVISOR_PROMPT
from agents.sources.hh import fetch_hh
from agents.sources.news import fetch_news
from agents.sources.reviews import fetch_reviews
from agents.supervisor.permissions import authorize_tool
from agents.supervisor.tools import (
    finish_research,
    search_hh,
    search_news,
    search_reviews,
    think,
)


def _phase_update(phase: RunPhase) -> dict[str, str]:
    return {"phase": phase.value}


def _completed_sources_text(completed_sources: list[SourceType]) -> str:
    if not completed_sources:
        return "none"
    return ", ".join(source.value for source in completed_sources)


def _company_context_text(identity: CompanyIdentity, language: ResponseLanguage) -> str:
    context_parts: list[str] = []
    if identity.profile_summary is not None:
        context_parts.append(identity.profile_summary)
    if identity.user_description is not None:
        if language == ResponseLanguage.EN:
            context_parts.append(f"User note: {identity.user_description}")
        else:
            context_parts.append(f"Уточнение от пользователя: {identity.user_description}")
    if identity.company_url is not None:
        if language == ResponseLanguage.EN:
            context_parts.append(f"Website: {identity.company_url}")
        else:
            context_parts.append(f"Сайт: {identity.company_url}")
    if not context_parts:
        if language == ResponseLanguage.EN:
            return "not provided"
        return "не указан"
    return " | ".join(context_parts)


def supervisor_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["supervisor_tools", "structure_events"]]:
    settings: Configuration = Configuration.from_runnable_config(config)
    if state["finished"]:
        return Command(goto="structure_events")
    if state["iteration_count"] >= settings.max_tool_iterations:
        return Command(goto="structure_events")

    identity: CompanyIdentity = load_company_identity(state["identity"])
    request = load_run_request(state["request"])
    completed_sources: list[SourceType] = load_completed_sources(state["completed_sources"])
    findings: list[RawFinding] = load_raw_findings(state["findings"])

    tools = [search_news, search_reviews, search_hh, think, finish_research]
    tools_model = create_llm_with_tools(tools=tools, config=config)
    system_message = SystemMessage(
        content=SUPERVISOR_PROMPT.format(
            company_name=identity.canonical_name,
            completed_sources=_completed_sources_text(completed_sources),
            findings_count=len(findings),
            company_context=_company_context_text(
                identity=identity,
                language=request.response_language,
            ),
        )
    )
    user_message = HumanMessage(content="Choose the next research tool call.")
    response = tools_model.invoke([system_message, user_message])
    if not isinstance(response, AIMessage):
        raise TypeError("Supervisor model returned unexpected response type")
    updated_history: list[AIMessage | ToolMessage] = [*state["conversation_history"], response]
    return Command(
        goto="supervisor_tools",
        update={
            "conversation_history": updated_history,
            "iteration_count": state["iteration_count"] + 1,
            **_phase_update(RunPhase.SUPERVISOR),
        },
    )


def _execute_source_tool(
    tool_name: str,
    identity: CompanyIdentity,
    settings: Configuration,
    response_language: ResponseLanguage,
) -> tuple[SourceType, list[RawFinding]]:
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


def _tool_observation_message(
    observation: ToolObservation,
    tool_call_id: str,
    tool_name: str,
) -> ToolMessage:
    return ToolMessage(
        content=json.dumps(observation.model_dump(mode="json")),
        tool_call_id=tool_call_id,
        name=tool_name,
    )


def supervisor_tools_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["supervisor", "structure_events"]]:
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

    settings: Configuration = Configuration.from_runnable_config(config)
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
                _tool_observation_message(
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
                source_type, source_findings = _execute_source_tool(
                    tool_name=tool_name,
                    identity=identity,
                    settings=settings,
                    response_language=request.response_language,
                )
            except Exception as error:
                updated_history.append(
                    _tool_observation_message(
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
                _tool_observation_message(
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
                _tool_observation_message(
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
                _tool_observation_message(
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
            _tool_observation_message(
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
