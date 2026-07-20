"""Research run lifecycle: start, resume, identity confirm, status, and background workers."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Literal
from uuid import UUID, uuid4

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph
from langgraph.types import Command

from agents.checkpoint_serde import create_checkpoint_serde
from agents.configuration import Configuration
from agents.model_credentials import (
    ResolvedLlmModel,
    load_model_credentials,
    require_model_credentials,
    resolve_llm_model,
)
from agents.graph_state import (
    ResearchRunState,
    dump_canonical_timeline,
    dump_company_identity,
    dump_employer_verdict,
    dump_hh_vacancy_analysis,
    dump_run_request,
    load_canonical_timeline,
    load_company_candidates,
    load_company_events,
    load_company_identity,
    load_completed_sources,
    load_employer_verdict,
    load_hh_vacancy_analysis,
    load_raw_findings,
    load_run_request,
    is_hh_vacancy_analysis_pending,
)
from agents.hh_vacancies.analysis import (
    build_hh_vacancy_analysis,
    build_pending_hh_vacancy_analysis,
)
from agents.hh_vacancies.client import HhApiClient
from agents.identity.resolution import (
    candidate_to_identity,
    find_candidate_by_id,
    normalize_company_name,
)
from agents.models import (
    CanonicalTimeline,
    CompanyIdentity,
    ResearchRunResult,
    RunLifecycleStatus,
    RunPhase,
    RunRequest,
    RunStatusResponse,
    utc_now,
)
from agents.observability import (
    build_langfuse_run_metadata,
    build_langfuse_run_name,
    trace_research_run,
)
from agents.pipeline import _should_skip_identity_resolution, build_research_graph
from backend.runtime_requirements import (
    ensure_checkpointer_directory,
    require_tavily_api_key,
)
from agents.verdict.verdict import build_insufficient_data_verdict


@dataclass(frozen=True)
class RunExecutionContext:
    """RunnableConfig plus thread id for one research run against the checkpointer."""

    run_id: UUID
    thread_id: str
    run_config: RunnableConfig


_run_lock: threading.Lock = threading.Lock()
_run_status_by_id: dict[UUID, RunLifecycleStatus] = {}
_run_errors_by_id: dict[UUID, str] = {}
_run_company_name_by_id: dict[UUID, str] = {}

_STATUS_REQUIRED_KEYS: tuple[str, ...] = (
    "identity",
    "findings",
    "events",
    "timeline",
    "verdict",
    "hh_vacancy_analysis",
    "completed_sources",
    "request",
    "iteration_count",
)


@contextmanager
def _sqlite_checkpointer(database_path: str) -> Iterator[SqliteSaver]:
    connection = sqlite3.connect(database_path, check_same_thread=False, timeout=30.0)
    connection.execute("PRAGMA journal_mode=WAL")
    checkpointer = SqliteSaver(connection, serde=create_checkpoint_serde())
    checkpointer.setup()
    try:
        yield checkpointer
    finally:
        connection.close()


@contextmanager
def _compiled_research_graph(settings: Configuration) -> Iterator[object]:
    ensure_checkpointer_directory(settings.sqlite_checkpointer_path)
    graph: StateGraph = build_research_graph()
    with _sqlite_checkpointer(settings.sqlite_checkpointer_path) as checkpointer:
        yield graph.compile(checkpointer=checkpointer)


def _set_run_status(run_id: UUID, status: RunLifecycleStatus, error_message: str | None) -> None:
    with _run_lock:
        _run_status_by_id[run_id] = status
        if error_message is None:
            _run_errors_by_id.pop(run_id, None)
        else:
            _run_errors_by_id[run_id] = error_message


def _register_run_metadata(run_id: UUID, company_name: str) -> None:
    with _run_lock:
        _run_company_name_by_id[run_id] = company_name
        _run_status_by_id[run_id] = RunLifecycleStatus.RUNNING
        _run_errors_by_id.pop(run_id, None)


def _get_run_company_name(run_id: UUID) -> str:
    with _run_lock:
        return _run_company_name_by_id.get(run_id, "")


def _get_run_status(run_id: UUID) -> RunLifecycleStatus | None:
    with _run_lock:
        return _run_status_by_id.get(run_id)


def _get_run_error(run_id: UUID) -> str | None:
    with _run_lock:
        return _run_errors_by_id.get(run_id)


def build_initial_state(request: RunRequest, run_id: UUID) -> ResearchRunState:
    """Build the initial ResearchRunState with a placeholder identity and empty findings."""
    placeholder_identity = CompanyIdentity(
        query_name=request.company_name,
        canonical_name=request.company_name,
        normalized_name=normalize_company_name(request.company_name),
        company_url=request.company_url,
        profile_summary=None,
        user_description=request.company_description,
    )
    return {
        "run_id": str(run_id),
        "phase": RunPhase.PENDING.value,
        "status": RunLifecycleStatus.RUNNING.value,
        "error_message": None,
        "request": dump_run_request(request),
        "identity": dump_company_identity(placeholder_identity),
        "identity_candidates": [],
        "findings": [],
        "events": [],
        "timeline": dump_canonical_timeline(CanonicalTimeline(events=[], conflicts=[])),
        "verdict": dump_employer_verdict(
            build_insufficient_data_verdict(
                company_name=request.company_name,
                language=request.response_language,
            )
        ),
        "hh_vacancy_analysis": dump_hh_vacancy_analysis(
            build_pending_hh_vacancy_analysis(search_query=request.company_name)
        ),
        "completed_sources": [],
        "conversation_history": [],
        "iteration_count": 0,
        "finished": False,
        "budget_deadline_unix": None,
        "estimated_tokens_used": 0,
        "budget_stop_reason": None,
    }


def _build_run_configurable(
    settings: Configuration,
    run_id: UUID,
    resolved_model: ResolvedLlmModel,
) -> dict[str, object]:
    return {
        "thread_id": str(run_id),
        "llm_model": resolved_model.model_name,
        "api_key": resolved_model.api_key,
        "structured_llm_max_tokens": settings.structured_llm_max_tokens,
        "tools_llm_max_tokens": settings.tools_llm_max_tokens,
        "max_tool_iterations": settings.max_tool_iterations,
        "max_run_wall_clock_seconds": settings.max_run_wall_clock_seconds,
        "max_estimated_run_tokens": settings.max_estimated_run_tokens,
    }


def _build_run_execution_context(
    settings: Configuration,
    run_id: UUID,
    request: RunRequest | None,
    langfuse_handler: BaseCallbackHandler | None,
) -> RunExecutionContext:
    credentials = load_model_credentials()
    require_model_credentials(credentials=credentials)
    resolved_model = resolve_llm_model(
        configured_model=settings.llm_model,
        credentials=credentials,
    )
    callbacks: list[BaseCallbackHandler] = []
    if langfuse_handler is not None and settings.langfuse_tracing_enabled:
        callbacks.append(langfuse_handler)
    thread_id: str = str(run_id)
    recursion_limit: int = (2 * settings.max_tool_iterations) + 12
    run_config: RunnableConfig = {
        "configurable": _build_run_configurable(
            settings=settings,
            run_id=run_id,
            resolved_model=resolved_model,
        ),
        "callbacks": callbacks,
        "recursion_limit": recursion_limit,
    }
    if request is not None:
        run_config["metadata"] = build_langfuse_run_metadata(run_id=run_id, request=request)
        run_config["run_name"] = build_langfuse_run_name(request=request)
    return RunExecutionContext(run_id=run_id, thread_id=thread_id, run_config=run_config)


def _build_checkpointer_context(settings: Configuration, run_id: UUID) -> RunExecutionContext:
    return _build_run_execution_context(
        settings=settings,
        run_id=run_id,
        request=None,
        langfuse_handler=None,
    )


def _launch_background_thread(thread_name: str, target: Callable[[], None]) -> None:
    worker_thread = threading.Thread(target=target, name=thread_name, daemon=True)
    worker_thread.start()


def _fail_background_run(
    run_id: UUID,
    error: Exception,
    on_complete: Callable[[UUID, ResearchRunResult | None, str | None], None],
) -> None:
    error_message: str = str(error)
    _set_run_status(
        run_id=run_id,
        status=RunLifecycleStatus.FAILED,
        error_message=error_message,
    )
    on_complete(run_id, None, error_message)


def _require_awaiting_identity_confirmation(state: ResearchRunState, run_id: UUID) -> None:
    status: RunLifecycleStatus = _status_from_state(state=state)
    if status != RunLifecycleStatus.AWAITING_INPUT:
        raise ValueError(f"Run {run_id} is not awaiting identity confirmation.")


def _state_to_result(state: ResearchRunState) -> ResearchRunResult:
    return ResearchRunResult(
        identity=load_company_identity(state["identity"]),
        findings=load_raw_findings(state["findings"]),
        events=load_company_events(state["events"]),
        timeline=load_canonical_timeline(state["timeline"]),
        verdict=load_employer_verdict(state["verdict"]),
        hh_vacancy_analysis=load_hh_vacancy_analysis(state["hh_vacancy_analysis"]),
    )


def _phase_from_state(state: ResearchRunState) -> RunPhase:
    phase_value: object = state.get("phase", RunPhase.PENDING.value)
    if not isinstance(phase_value, str) or phase_value.strip() == "":
        return RunPhase.PENDING
    try:
        return RunPhase(phase_value)
    except ValueError:
        return RunPhase.PENDING


def _status_from_state(state: ResearchRunState) -> RunLifecycleStatus:
    status_value: object = state.get("status", RunLifecycleStatus.RUNNING.value)
    if not isinstance(status_value, str) or status_value.strip() == "":
        return RunLifecycleStatus.RUNNING
    try:
        return RunLifecycleStatus(status_value)
    except ValueError:
        return RunLifecycleStatus.RUNNING


def _hh_vacancy_analysis_pending(state: ResearchRunState) -> bool:
    """Return True when HH analysis has not yet been fetched for this run."""
    return is_hh_vacancy_analysis_pending(state=state)


def _graph_resume_input(
    state: ResearchRunState,
    next_nodes: tuple[str, ...],
) -> Command[Literal["supervisor", "analyze_hh_vacancies"]] | None:
    if next_nodes:
        return None
    # No pending nodes: skip identity interrupt and resume into HH or supervisor.
    if _should_skip_identity_resolution(state=state):
        if _hh_vacancy_analysis_pending(state=state):
            return Command(goto="analyze_hh_vacancies")
        return Command(goto="supervisor")
    return None


def _finalize_graph_run(
    run_id: UUID,
    final_state: ResearchRunState,
) -> ResearchRunResult | None:
    status: RunLifecycleStatus = _status_from_state(state=final_state)
    error_message: str | None = final_state.get("error_message")
    if status == RunLifecycleStatus.AWAITING_INPUT:
        _set_run_status(
            run_id=run_id,
            status=RunLifecycleStatus.AWAITING_INPUT,
            error_message=error_message,
        )
        return None
    if status == RunLifecycleStatus.FAILED:
        _set_run_status(
            run_id=run_id,
            status=RunLifecycleStatus.FAILED,
            error_message=error_message,
        )
        return None
    if status == RunLifecycleStatus.RUNNING:
        _set_run_status(
            run_id=run_id,
            status=RunLifecycleStatus.RUNNING,
            error_message=error_message,
        )
        return None
    _set_run_status(run_id=run_id, status=RunLifecycleStatus.COMPLETED, error_message=None)
    return _state_to_result(state=final_state)


def _checkpoint_ready_for_status(state: dict[str, object]) -> bool:
    return all(key in state for key in _STATUS_REQUIRED_KEYS)


def _tracked_status_response(run_id: UUID) -> RunStatusResponse:
    tracked_status: RunLifecycleStatus | None = _get_run_status(run_id=run_id)
    if tracked_status is None:
        raise LookupError(f"Run not found: {run_id}")
    return RunStatusResponse(
        run_id=run_id,
        created_at=utc_now(),
        status=tracked_status,
        phase=RunPhase.PENDING,
        company_name=_get_run_company_name(run_id=run_id),
        completed_sources=[],
        findings_count=0,
        events_count=0,
        iteration_count=0,
        error_message=_get_run_error(run_id=run_id),
        identity_candidates=[],
        result=None,
    )


def _build_status_response(
    run_id: UUID,
    state: ResearchRunState,
    next_nodes: tuple[str, ...],
) -> RunStatusResponse:
    _ = next_nodes
    if not _checkpoint_ready_for_status(state=dict(state)):
        return _tracked_status_response(run_id=run_id)

    phase: RunPhase = _phase_from_state(state=state)
    status: RunLifecycleStatus = _status_from_state(state=state)
    result: ResearchRunResult | None = None
    if status == RunLifecycleStatus.COMPLETED:
        phase = RunPhase.COMPLETED
        result = _state_to_result(state=state)
    identity = load_company_identity(state["identity"])
    completed_sources = load_completed_sources(state["completed_sources"])
    identity_candidates = load_company_candidates(state.get("identity_candidates", []))
    return RunStatusResponse(
        run_id=run_id,
        created_at=utc_now(),
        status=status,
        phase=phase,
        company_name=identity.canonical_name,
        completed_sources=completed_sources,
        findings_count=len(state["findings"]),
        events_count=len(state["events"]),
        iteration_count=int(state["iteration_count"]),
        error_message=state.get("error_message"),
        identity_candidates=identity_candidates,
        result=result,
    )


def _execute_graph(
    settings: Configuration,
    run_id: UUID,
    initial_state: ResearchRunState | None,
) -> ResearchRunResult | None:
    require_tavily_api_key()
    _set_run_status(run_id=run_id, status=RunLifecycleStatus.RUNNING, error_message=None)

    with _compiled_research_graph(settings=settings) as compiled_graph:
        if initial_state is not None:
            request: RunRequest = load_run_request(initial_state["request"])
        else:
            checkpointer_context: RunExecutionContext = _build_checkpointer_context(
                settings=settings,
                run_id=run_id,
            )
            state_snapshot = compiled_graph.get_state(config=checkpointer_context.run_config)
            if state_snapshot.values is None or not state_snapshot.values:
                raise LookupError(f"Run not found: {run_id}")
            request = load_run_request(state_snapshot.values["request"])
            resume_input: Command[Literal["supervisor", "analyze_hh_vacancies"]] | None = _graph_resume_input(
                state=state_snapshot.values,
                next_nodes=tuple(state_snapshot.next or ()),
            )

        with trace_research_run(run_id=run_id, request=request) as langfuse_handler:
            execution_context: RunExecutionContext = _build_run_execution_context(
                settings=settings,
                run_id=run_id,
                request=request,
                langfuse_handler=langfuse_handler,
            )
            if initial_state is None:
                # resume_input is None to continue pending nodes, or Command(goto=supervisor).
                final_state: ResearchRunState = compiled_graph.invoke(
                    resume_input,
                    config=execution_context.run_config,
                )
            else:
                final_state = compiled_graph.invoke(
                    initial_state,
                    config=execution_context.run_config,
                )

    return _finalize_graph_run(run_id=run_id, final_state=final_state)


def run_research_pipeline(request: RunRequest, run_id: UUID | None) -> tuple[UUID, ResearchRunResult]:
    """Run the research graph to completion synchronously and return the run id plus result."""
    settings = Configuration()
    selected_run_id: UUID = run_id if run_id is not None else uuid4()
    initial_state: ResearchRunState = build_initial_state(
        request=request,
        run_id=selected_run_id,
    )
    result: ResearchRunResult | None = _execute_graph(
        settings=settings,
        run_id=selected_run_id,
        initial_state=initial_state,
    )
    if result is None:
        tracked_status: RunLifecycleStatus | None = _get_run_status(run_id=selected_run_id)
        if tracked_status == RunLifecycleStatus.AWAITING_INPUT:
            raise RuntimeError(
                "Identity confirmation required before research can continue. "
                f"Poll GET /runs/{selected_run_id} and POST /runs/{selected_run_id}/identity."
            )
        error_message: str | None = _get_run_error(run_id=selected_run_id)
        raise RuntimeError(error_message or "Research run failed during identity resolution.")
    return selected_run_id, result


def resume_research_run(run_id: UUID) -> ResearchRunResult:
    """Resume a checkpointed run to completion and return the final ResearchRunResult."""
    settings = Configuration()
    result: ResearchRunResult | None = _execute_graph(
        settings=settings,
        run_id=run_id,
        initial_state=None,
    )
    if result is None:
        error_message: str | None = _get_run_error(run_id=run_id)
        raise RuntimeError(error_message or f"Run {run_id} did not produce a completed result.")
    return result


def _load_checkpoint_state(run_id: UUID) -> tuple[Configuration, RunExecutionContext, ResearchRunState]:
    settings = Configuration()
    execution_context: RunExecutionContext = _build_checkpointer_context(
        settings=settings,
        run_id=run_id,
    )
    with _compiled_research_graph(settings=settings) as compiled_graph:
        state_snapshot = compiled_graph.get_state(config=execution_context.run_config)
        if state_snapshot.values is None or not state_snapshot.values:
            raise LookupError(f"Run not found: {run_id}")
        state: ResearchRunState = state_snapshot.values
    return settings, execution_context, state


def validate_identity_confirmation_request(run_id: UUID, candidate_id: str) -> None:
    """Ensure the run awaits identity input and that candidate_id exists among candidates."""
    _settings, _execution_context, state = _load_checkpoint_state(run_id=run_id)
    _require_awaiting_identity_confirmation(state=state, run_id=run_id)
    candidates = load_company_candidates(state.get("identity_candidates", []))
    find_candidate_by_id(
        candidates=candidates,
        candidate_id=candidate_id,
    )


def confirm_company_identity_selection(run_id: UUID, candidate_id: str) -> RunRequest:
    """Persist the selected candidate as identity and clear the awaiting-input interrupt."""
    settings, execution_context, state = _load_checkpoint_state(run_id=run_id)
    _require_awaiting_identity_confirmation(state=state, run_id=run_id)

    candidates = load_company_candidates(state.get("identity_candidates", []))
    selected_candidate = find_candidate_by_id(
        candidates=candidates,
        candidate_id=candidate_id,
    )
    request = load_run_request(state["request"])
    identity = candidate_to_identity(
        candidate=selected_candidate,
        query_name=request.company_name,
        requested_company_url=request.company_url,
        user_description=request.company_description,
    )

    with _compiled_research_graph(settings=settings) as compiled_graph:
        compiled_graph.update_state(
            execution_context.run_config,
            {
                "identity": dump_company_identity(identity),
                "identity_candidates": [],
                "status": RunLifecycleStatus.RUNNING.value,
                "phase": RunPhase.ANALYZE_HH_VACANCIES.value,
                "error_message": None,
            },
        )
    _set_run_status(run_id=run_id, status=RunLifecycleStatus.RUNNING, error_message=None)
    return request


def confirm_and_continue_research_run_background(
    run_id: UUID,
    candidate_id: str,
    on_complete: Callable[[UUID, ResearchRunResult | None, str | None], None],
) -> None:
    """Confirm identity synchronously, then resume research on a daemon thread.

    Confirmation must finish before the HTTP handler returns so the next GET /runs
    poll sees RUNNING — otherwise the UI treats a stale awaiting_input as a stop
    and freezes on the identity picker.
    """
    confirm_company_identity_selection(run_id=run_id, candidate_id=candidate_id)

    def _background_worker() -> None:
        try:
            result: ResearchRunResult = resume_research_run(run_id=run_id)
            on_complete(run_id, result, None)
        except Exception as error:
            _fail_background_run(run_id=run_id, error=error, on_complete=on_complete)

    # Identity is already confirmed; research continues on this daemon thread.
    _launch_background_thread(
        thread_name=f"research-run-confirm-{run_id}",
        target=_background_worker,
    )


def continue_research_run_background(
    run_id: UUID,
    on_complete: Callable[[UUID, ResearchRunResult | None, str | None], None],
) -> None:
    """Resume a checkpointed run on a daemon thread and invoke on_complete when finished."""
    settings = Configuration()

    def _background_worker() -> None:
        try:
            result: ResearchRunResult | None = _execute_graph(
                settings=settings,
                run_id=run_id,
                initial_state=None,
            )
            if result is None:
                tracked_status: RunLifecycleStatus | None = _get_run_status(run_id=run_id)
                if tracked_status == RunLifecycleStatus.FAILED:
                    raise RuntimeError(_get_run_error(run_id=run_id) or "Research run failed.")
                if tracked_status == RunLifecycleStatus.AWAITING_INPUT:
                    on_complete(run_id, None, None)
                    return
                raise RuntimeError("Research stopped before completion.")
            on_complete(run_id, result, None)
        except Exception as error:
            _fail_background_run(run_id=run_id, error=error, on_complete=on_complete)

    _launch_background_thread(
        thread_name=f"research-run-continue-{run_id}",
        target=_background_worker,
    )


def retry_hh_employer_search(run_id: UUID, employer_query: str) -> ResearchRunResult:
    """Re-run hh.ru employer search for a completed run using a manual query override."""
    settings = Configuration()
    execution_context: RunExecutionContext = _build_checkpointer_context(
        settings=settings,
        run_id=run_id,
    )

    with _compiled_research_graph(settings=settings) as compiled_graph:
        state_snapshot = compiled_graph.get_state(config=execution_context.run_config)
        if state_snapshot.values is None or not state_snapshot.values:
            raise LookupError(f"Run not found: {run_id}")
        state: ResearchRunState = state_snapshot.values
        status: RunLifecycleStatus = _status_from_state(state=state)
        if status != RunLifecycleStatus.COMPLETED:
            raise ValueError(f"Run {run_id} must be completed before HH search retry.")

        identity = load_company_identity(state["identity"])
        request = load_run_request(state["request"])
        client: HhApiClient = HhApiClient(settings)
        try:
            analysis = build_hh_vacancy_analysis(
                identity=identity,
                settings=settings,
                client=client,
                config=execution_context.run_config,
                search_query_override=employer_query,
                response_language=request.response_language,
            )
        finally:
            client.close()

        compiled_graph.update_state(
            execution_context.run_config,
            {"hh_vacancy_analysis": dump_hh_vacancy_analysis(analysis)},
        )
        updated_snapshot = compiled_graph.get_state(config=execution_context.run_config)
        if updated_snapshot.values is None or not updated_snapshot.values:
            raise RuntimeError(f"Failed to persist HH analysis for run {run_id}")
        return _state_to_result(state=updated_snapshot.values)


def get_research_run_status(run_id: UUID) -> RunStatusResponse:
    """Load checkpoint state for a run and return the current lifecycle status response."""
    settings = Configuration()
    execution_context: RunExecutionContext = _build_checkpointer_context(
        settings=settings,
        run_id=run_id,
    )

    with _compiled_research_graph(settings=settings) as compiled_graph:
        state_snapshot = compiled_graph.get_state(config=execution_context.run_config)
        if state_snapshot.values is None or not state_snapshot.values:
            return _tracked_status_response(run_id=run_id)
        state: ResearchRunState = state_snapshot.values
        if not _checkpoint_ready_for_status(state=dict(state)):
            return _tracked_status_response(run_id=run_id)
        next_nodes: tuple[str, ...] = tuple(state_snapshot.next or ())
        return _build_status_response(
            run_id=run_id,
            state=state,
            next_nodes=next_nodes,
        )


def start_research_run_background(
    request: RunRequest,
    run_id: UUID | None,
    on_complete: Callable[[UUID, ResearchRunResult | None, str | None], None],
) -> UUID:
    """Start a research run on a daemon thread and return the assigned run id immediately."""
    credentials = load_model_credentials()
    require_model_credentials(credentials=credentials)
    require_tavily_api_key()

    selected_run_id: UUID = run_id if run_id is not None else uuid4()
    settings = Configuration()
    initial_state: ResearchRunState = build_initial_state(
        request=request,
        run_id=selected_run_id,
    )
    # Register before the worker starts so the first poll never races on missing channels.
    _register_run_metadata(run_id=selected_run_id, company_name=request.company_name)

    def _background_worker() -> None:
        try:
            result: ResearchRunResult | None = _execute_graph(
                settings=settings,
                run_id=selected_run_id,
                initial_state=initial_state,
            )
            on_complete(selected_run_id, result, None)
        except Exception as error:
            _fail_background_run(
                run_id=selected_run_id,
                error=error,
                on_complete=on_complete,
            )

    # Caller polls GET /runs/{id}; this thread owns graph invoke side effects.
    _launch_background_thread(
        thread_name=f"research-run-{selected_run_id}",
        target=_background_worker,
    )
    return selected_run_id
