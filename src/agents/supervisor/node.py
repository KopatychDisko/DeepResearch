from __future__ import annotations

import json
import time
from typing import Literal

import tiktoken
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
from agents.observability import record_budget_stop_reason, trace_source_research
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

_RECENT_TOOL_OUTCOMES_LIMIT: int = 3
_TIKTOKEN_ENCODING_NAME: str = "cl100k_base"


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


def _format_recent_tool_outcomes(
    conversation_history: list[AIMessage | ToolMessage],
    max_outcomes: int,
) -> str:
    tool_messages: list[ToolMessage] = [
        message for message in conversation_history if isinstance(message, ToolMessage)
    ]
    if not tool_messages:
        return "none"
    recent_messages: list[ToolMessage] = tool_messages[-max_outcomes:]
    lines: list[str] = []
    for message in recent_messages:
        payload: dict[str, object]
        try:
            parsed = json.loads(str(message.content))
        except json.JSONDecodeError:
            lines.append(f"- status=unknown tool={message.name or 'unknown'} summary={message.content}")
            continue
        if not isinstance(parsed, dict):
            lines.append(f"- status=unknown tool={message.name or 'unknown'} summary={message.content}")
            continue
        payload = parsed
        status_value = payload.get("status", "unknown")
        tool_value = payload.get("tool", message.name or "unknown")
        summary_value = payload.get("summary", "")
        lines.append(f"- status={status_value} tool={tool_value} summary={summary_value}")
    return "\n".join(lines)


def _estimate_text_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding(_TIKTOKEN_ENCODING_NAME)
    return len(encoding.encode(text))


def _tokens_from_supervisor_turn(
    response: AIMessage,
    prompt_texts: list[str],
) -> int:
    usage_metadata = response.usage_metadata
    if usage_metadata is not None:
        total_tokens = usage_metadata.get("total_tokens")
        if total_tokens is not None:
            return int(total_tokens)
        input_tokens = usage_metadata.get("input_tokens")
        output_tokens = usage_metadata.get("output_tokens")
        if input_tokens is not None and output_tokens is not None:
            return int(input_tokens) + int(output_tokens)
    prompt_token_count: int = sum(_estimate_text_tokens(text) for text in prompt_texts)
    response_token_count: int = _estimate_text_tokens(str(response.content))
    return prompt_token_count + response_token_count


def _budget_stop_command(
    budget_stop_reason: str,
    extra_update: dict[str, object],
) -> Command[Literal["structure_events"]]:
    record_budget_stop_reason(budget_stop_reason=budget_stop_reason)
    return Command(
        goto="structure_events",
        update={
            **extra_update,
            "budget_stop_reason": budget_stop_reason,
        },
    )


def supervisor_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["supervisor_tools", "structure_events"]]:
    settings: Configuration = Configuration.from_runnable_config(config)
    if state["finished"]:
        return Command(goto="structure_events")

    now: float = time.time()
    deadline: float | None = state.get("budget_deadline_unix")
    budget_state_update: dict[str, object] = {}
    if deadline is None:
        deadline = now + float(settings.max_run_wall_clock_seconds)
        budget_state_update["budget_deadline_unix"] = deadline

    if state["iteration_count"] >= settings.max_tool_iterations:
        return _budget_stop_command(
            budget_stop_reason="max_tool_iterations",
            extra_update=budget_state_update,
        )
    if deadline is not None and now >= deadline:
        return _budget_stop_command(
            budget_stop_reason="wall_clock",
            extra_update=budget_state_update,
        )
    estimated_tokens_used: int = int(state.get("estimated_tokens_used") or 0)
    if estimated_tokens_used >= settings.max_estimated_run_tokens:
        return _budget_stop_command(
            budget_stop_reason="soft_token_budget",
            extra_update=budget_state_update,
        )

    identity: CompanyIdentity = load_company_identity(state["identity"])
    request = load_run_request(state["request"])
    completed_sources: list[SourceType] = load_completed_sources(state["completed_sources"])
    findings: list[RawFinding] = load_raw_findings(state["findings"])
    recent_tool_outcomes: str = _format_recent_tool_outcomes(
        conversation_history=state["conversation_history"],
        max_outcomes=_RECENT_TOOL_OUTCOMES_LIMIT,
    )

    tools = [search_news, search_reviews, search_hh, think, finish_research]
    tools_model = create_llm_with_tools(tools=tools, config=config)
    system_prompt_text: str = SUPERVISOR_PROMPT.format(
        company_name=identity.canonical_name,
        completed_sources=_completed_sources_text(completed_sources),
        findings_count=len(findings),
        company_context=_company_context_text(
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
    turn_tokens: int = _tokens_from_supervisor_turn(
        response=response,
        prompt_texts=[system_prompt_text, user_message_text],
    )
    updated_history: list[AIMessage | ToolMessage] = [*state["conversation_history"], response]
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
    settings: Configuration = Configuration.from_runnable_config(config)
    deadline: float | None = state.get("budget_deadline_unix")
    if deadline is not None and time.time() >= float(deadline):
        return _budget_stop_command(
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
