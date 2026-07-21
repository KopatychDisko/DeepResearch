"""Graph invoke, resume routing, and run finalization."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from langgraph.types import Command

from agents.configuration import Configuration
from agents.graph.pipeline import _should_skip_identity_resolution
from agents.graph.state import ResearchRunState, load_run_request
from agents.models import ResearchRunResult, RunLifecycleStatus, RunRequest
from agents.observability import trace_research_run
from backend.run.checkpointer import compiled_research_graph
from backend.run.context import RunExecutionContext, build_checkpointer_context, build_run_execution_context
from backend.run.registry import set_run_status
from backend.run.state_mapping import (
    hh_vacancy_analysis_pending,
    state_to_result,
    status_from_state,
)
from backend.runtime_requirements import require_tavily_api_key


def graph_resume_input(
    state: ResearchRunState,
    next_nodes: tuple[str, ...],
) -> Command[Literal["supervisor", "analyze_hh_vacancies"]] | None:
    """Return a resume Command when identity is confirmed but no nodes are pending."""
    if next_nodes:
        return None

    if _should_skip_identity_resolution(state=state):
        if hh_vacancy_analysis_pending(state=state):
            return Command(goto="analyze_hh_vacancies")
        return Command(goto="supervisor")

    return None


def finalize_graph_run(
    run_id: UUID,
    final_state: ResearchRunState,
) -> ResearchRunResult | None:
    """Update registry from final checkpoint state and return result when completed."""
    status: RunLifecycleStatus = status_from_state(state=final_state)
    error_message: str | None = final_state.get("error_message")

    if status == RunLifecycleStatus.AWAITING_INPUT:
        set_run_status(
            run_id=run_id,
            status=RunLifecycleStatus.AWAITING_INPUT,
            error_message=error_message,
        )
        return None

    if status == RunLifecycleStatus.FAILED:
        set_run_status(
            run_id=run_id,
            status=RunLifecycleStatus.FAILED,
            error_message=error_message,
        )
        return None

    if status == RunLifecycleStatus.RUNNING:
        set_run_status(
            run_id=run_id,
            status=RunLifecycleStatus.RUNNING,
            error_message=error_message,
        )
        return None

    set_run_status(run_id=run_id, status=RunLifecycleStatus.COMPLETED, error_message=None)
    return state_to_result(state=final_state)


def execute_graph(
    settings: Configuration,
    run_id: UUID,
    initial_state: ResearchRunState | None,
) -> ResearchRunResult | None:
    """Invoke the research graph once and finalize registry state."""
    require_tavily_api_key()
    set_run_status(run_id=run_id, status=RunLifecycleStatus.RUNNING, error_message=None)

    with compiled_research_graph(settings=settings) as compiled_graph:
        if initial_state is not None:
            request: RunRequest = load_run_request(initial_state["request"])
            resume_input: Command[Literal["supervisor", "analyze_hh_vacancies"]] | None = None
        else:
            checkpointer_context: RunExecutionContext = build_checkpointer_context(
                settings=settings,
                run_id=run_id,
            )
            state_snapshot = compiled_graph.get_state(config=checkpointer_context.run_config)
            if state_snapshot.values is None or not state_snapshot.values:
                raise LookupError(f"Run not found: {run_id}")

            request = load_run_request(state_snapshot.values["request"])
            resume_input = graph_resume_input(
                state=state_snapshot.values,
                next_nodes=tuple(state_snapshot.next or ()),
            )

        with trace_research_run(run_id=run_id, request=request) as langfuse_handler:
            execution_context: RunExecutionContext = build_run_execution_context(
                settings=settings,
                run_id=run_id,
                request=request,
                langfuse_handler=langfuse_handler,
            )

            if initial_state is None:
                final_state: ResearchRunState = compiled_graph.invoke(
                    resume_input,
                    config=execution_context.run_config,
                )
            else:
                final_state = compiled_graph.invoke(
                    initial_state,
                    config=execution_context.run_config,
                )

    return finalize_graph_run(run_id=run_id, final_state=final_state)
