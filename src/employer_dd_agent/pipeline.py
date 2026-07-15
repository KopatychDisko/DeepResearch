from __future__ import annotations

import json
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import START, StateGraph
from langgraph.types import Command

from employer_dd_agent.configuration import Configuration
from employer_dd_agent.graph_state import (
    ResearchRunState,
    dump_canonical_timeline,
    dump_company_candidates,
    dump_company_events,
    dump_company_identity,
    dump_completed_sources,
    dump_employer_verdict,
    dump_raw_findings,
    load_canonical_timeline,
    load_company_events,
    load_company_identity,
    load_completed_sources,
    load_raw_findings,
    load_run_request,
)
from employer_dd_agent.language import response_language_instruction
from employer_dd_agent.identity import (
    IdentityResolutionStatus,
    resolve_company_identity_from_web,
)
from employer_dd_agent.llm_service import create_llm_with_tools
from employer_dd_agent.merge import merge_events_into_timeline
from employer_dd_agent.models import (
    CompanyEvent,
    CompanyIdentity,
    RawFinding,
    RunLifecycleStatus,
    RunPhase,
    ResponseLanguage,
    SourceType,
    StructuredCompanyEvents,
)
from employer_dd_agent.observability import trace_source_research
from employer_dd_agent.prompts import STRUCTURE_EVENTS_PROMPT, SUPERVISOR_PROMPT
from employer_dd_agent.sources import fetch_hh, fetch_news, fetch_reviews
from employer_dd_agent.structured_output import invoke_structured_output
from employer_dd_agent.verdict import generate_employer_verdict


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


def _phase_update(phase: RunPhase) -> dict[str, str]:
    return {"phase": phase.value}


def _should_skip_identity_resolution(state: ResearchRunState) -> bool:
    status_value: str = state.get("status", "")
    phase_value: str = state.get("phase", "")
    if status_value != RunLifecycleStatus.RUNNING.value:
        return False
    if phase_value != RunPhase.SUPERVISOR.value:
        return False
    identity_candidates = state.get("identity_candidates", [])
    return not identity_candidates


def resolve_identity_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["supervisor", "__end__"]]:
    if _should_skip_identity_resolution(state=state):
        return Command(
            goto="supervisor",
            update=_phase_update(RunPhase.SUPERVISOR),
        )

    settings: Configuration = Configuration.from_runnable_config(config)
    request = load_run_request(state["request"])
    resolution = resolve_company_identity_from_web(
        company_name=request.company_name,
        company_url=request.company_url,
        company_description=request.company_description,
        response_language=request.response_language,
        config=config,
        settings=settings,
    )

    if resolution.status == IdentityResolutionStatus.NOT_FOUND:
        return Command(
            goto="__end__",
            update={
                "status": RunLifecycleStatus.FAILED.value,
                "phase": RunPhase.AWAITING_IDENTITY.value,
                "error_message": resolution.message,
                "identity_candidates": [],
                **_phase_update(RunPhase.RESOLVE_IDENTITY),
            },
        )

    if resolution.status == IdentityResolutionStatus.AMBIGUOUS:
        return Command(
            goto="__end__",
            update={
                "status": RunLifecycleStatus.AWAITING_INPUT.value,
                "phase": RunPhase.AWAITING_IDENTITY.value,
                "error_message": resolution.message,
                "identity_candidates": dump_company_candidates(resolution.candidates),
                **_phase_update(RunPhase.AWAITING_IDENTITY),
            },
        )

    if resolution.identity is None:
        raise RuntimeError("Confirmed identity resolution returned no identity")

    return Command(
        goto="supervisor",
        update={
            "identity": dump_company_identity(resolution.identity),
            "identity_candidates": dump_company_candidates(resolution.candidates),
            **_phase_update(RunPhase.RESOLVE_IDENTITY),
        },
    )


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

        if tool_name in {"search_news", "search_reviews", "search_hh"}:
            source_type, source_findings = _execute_source_tool(
                tool_name=tool_name,
                identity=identity,
                settings=settings,
                response_language=request.response_language,
            )
            updated_findings.extend(source_findings)
            if source_type not in updated_sources:
                updated_sources.append(source_type)
            updated_history.append(
                ToolMessage(
                    content=f"Collected {len(source_findings)} findings from {source_type.value}",
                    tool_call_id=tool_id,
                    name=tool_name,
                )
            )
            continue

        if tool_name == "think":
            reflection: str = str(tool_args_value.get("reflection", ""))
            updated_history.append(
                ToolMessage(content=reflection, tool_call_id=tool_id, name=tool_name)
            )
            continue

        if tool_name == "finish_research":
            finish_requested = True
            reason: str = str(tool_args_value.get("reason", "No reason provided"))
            updated_history.append(
                ToolMessage(content=reason, tool_call_id=tool_id, name=tool_name)
            )
            continue

        raise ValueError(f"Unsupported supervisor tool call: {tool_name}")

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


def _truncate_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}…"


def _findings_text(findings: list[RawFinding]) -> str:
    max_findings: int = 20
    max_snippet_length: int = 600
    selected_findings: list[RawFinding] = findings[:max_findings]
    serialized_findings: list[dict[str, str]] = []
    for finding in selected_findings:
        serialized_findings.append(
            {
                "source_type": finding.source_type.value,
                "source_url": str(finding.source_url),
                "title": _truncate_text(finding.title, 200),
                "snippet": _truncate_text(finding.snippet, max_snippet_length),
            }
        )
    return json.dumps(serialized_findings, ensure_ascii=False, indent=2)


def structure_events_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["merge_timeline"]]:
    findings: list[RawFinding] = load_raw_findings(state["findings"])
    if not findings:
        return Command(
            goto="merge_timeline",
            update={"events": [], **_phase_update(RunPhase.STRUCTURE_EVENTS)},
        )

    identity: CompanyIdentity = load_company_identity(state["identity"])
    request = load_run_request(state["request"])
    parsed_output = invoke_structured_output(
        config=config,
        model_class=StructuredCompanyEvents,
        prompt=STRUCTURE_EVENTS_PROMPT.format(
            company_name=identity.canonical_name,
            findings_text=_findings_text(findings),
            response_language_instruction=response_language_instruction(
                language=request.response_language
            ),
        ),
    )

    allowed_urls: set[str] = {str(finding.source_url) for finding in findings}
    filtered_events: list[CompanyEvent] = []
    for event in parsed_output.events:
        if str(event.source_url) in allowed_urls:
            filtered_events.append(event)
    return Command(
        goto="merge_timeline",
        update={
            "events": dump_company_events(filtered_events),
            **_phase_update(RunPhase.STRUCTURE_EVENTS),
        },
    )


def merge_timeline_step(state: ResearchRunState) -> Command[Literal["generate_verdict"]]:
    events = load_company_events(state["events"])
    timeline = merge_events_into_timeline(events)
    return Command(
        goto="generate_verdict",
        update={
            "timeline": dump_canonical_timeline(timeline),
            **_phase_update(RunPhase.MERGE_TIMELINE),
        },
    )


def generate_verdict_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["__end__"]]:
    identity: CompanyIdentity = load_company_identity(state["identity"])
    request = load_run_request(state["request"])
    timeline = load_canonical_timeline(state["timeline"])
    verdict = generate_employer_verdict(
        company_name=identity.canonical_name,
        timeline=timeline,
        language=request.response_language,
        config=config,
    )
    return Command(
        goto="__end__",
        update={
            "verdict": dump_employer_verdict(verdict),
            "status": RunLifecycleStatus.COMPLETED.value,
            **_phase_update(RunPhase.GENERATE_VERDICT),
        },
    )


def build_research_graph() -> StateGraph:
    graph: StateGraph = StateGraph(ResearchRunState)
    graph.add_node("resolve_identity", resolve_identity_step)
    graph.add_node("supervisor", supervisor_step)
    graph.add_node("supervisor_tools", supervisor_tools_step)
    graph.add_node("structure_events", structure_events_step)
    graph.add_node("merge_timeline", merge_timeline_step)
    graph.add_node("generate_verdict", generate_verdict_step)
    graph.add_edge(START, "resolve_identity")
    graph.add_edge("supervisor", "supervisor_tools")
    graph.add_edge("structure_events", "merge_timeline")
    graph.add_edge("merge_timeline", "generate_verdict")
    return graph
