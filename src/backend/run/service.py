"""Public research run lifecycle API."""

from __future__ import annotations

import threading
from collections.abc import Callable
from uuid import UUID, uuid4

from agents.configuration import Configuration
from agents.graph.state import ResearchRunState
from agents.model_credentials import load_model_credentials, require_model_credentials
from agents.models import ResearchRunResult, RunLifecycleStatus, RunRequest, RunStatusResponse
from backend.run.checkpointer import compiled_research_graph
from backend.run.context import build_checkpointer_context
from backend.run.execution import execute_graph
from backend.run.identity import (
    confirm_company_identity_selection,
    load_checkpoint_state,
    validate_identity_confirmation_request,
)
from backend.run.initial_state import build_initial_state
from backend.run.registry import get_run_error, get_run_status, register_run_metadata, set_run_status
from backend.run.status import build_status_response, checkpoint_ready_for_status, tracked_status_response
from backend.runtime_requirements import require_tavily_api_key


def _launch_background_thread(thread_name: str, target: Callable[[], None]) -> None:
    worker_thread = threading.Thread(target=target, name=thread_name, daemon=True)
    worker_thread.start()


def _fail_background_run(
    run_id: UUID,
    error: Exception,
    on_complete: Callable[[UUID, ResearchRunResult | None, str | None], None],
) -> None:
    error_message: str = str(error)
    set_run_status(
        run_id=run_id,
        status=RunLifecycleStatus.FAILED,
        error_message=error_message,
    )
    on_complete(run_id, None, error_message)


def run_research_pipeline(request: RunRequest, run_id: UUID | None) -> tuple[UUID, ResearchRunResult]:
    """Run the research graph to completion synchronously and return the run id plus result."""
    settings = Configuration()
    selected_run_id: UUID = run_id if run_id is not None else uuid4()

    initial_state: ResearchRunState = build_initial_state(
        request=request,
        run_id=selected_run_id,
    )
    result: ResearchRunResult | None = execute_graph(
        settings=settings,
        run_id=selected_run_id,
        initial_state=initial_state,
    )

    if result is None:
        tracked_status: RunLifecycleStatus | None = get_run_status(run_id=selected_run_id)
        if tracked_status == RunLifecycleStatus.AWAITING_INPUT:
            raise RuntimeError(
                "Identity confirmation required before research can continue. "
                f"Poll GET /runs/{selected_run_id} and POST /runs/{selected_run_id}/identity."
            )
        error_message: str | None = get_run_error(run_id=selected_run_id)
        raise RuntimeError(error_message or "Research run failed during identity resolution.")

    return selected_run_id, result


def resume_research_run(run_id: UUID) -> ResearchRunResult:
    """Resume a checkpointed run to completion and return the final ResearchRunResult."""
    settings = Configuration()
    result: ResearchRunResult | None = execute_graph(
        settings=settings,
        run_id=run_id,
        initial_state=None,
    )
    if result is None:
        error_message: str | None = get_run_error(run_id=run_id)
        raise RuntimeError(error_message or f"Run {run_id} did not produce a completed result.")
    return result


def get_research_run_status(run_id: UUID) -> RunStatusResponse:
    """Load checkpoint state for a run and return the current lifecycle status response."""
    settings = Configuration()
    execution_context = build_checkpointer_context(settings=settings, run_id=run_id)

    with compiled_research_graph(settings=settings) as compiled_graph:
        state_snapshot = compiled_graph.get_state(config=execution_context.run_config)

        if state_snapshot.values is None or not state_snapshot.values:
            return tracked_status_response(run_id=run_id)

        state: ResearchRunState = state_snapshot.values
        if not checkpoint_ready_for_status(state=dict(state)):
            return tracked_status_response(run_id=run_id)

        next_nodes: tuple[str, ...] = tuple(state_snapshot.next or ())
        return build_status_response(
            run_id=run_id,
            state=state,
            next_nodes=next_nodes,
        )


def confirm_and_continue_research_run_background(
    run_id: UUID,
    candidate_id: str,
    on_complete: Callable[[UUID, ResearchRunResult | None, str | None], None],
) -> None:
    """Confirm identity synchronously, then resume research on a daemon thread."""
    confirm_company_identity_selection(run_id=run_id, candidate_id=candidate_id)

    def background_worker() -> None:
        try:
            result: ResearchRunResult = resume_research_run(run_id=run_id)
            on_complete(run_id, result, None)
        except Exception as error:
            _fail_background_run(run_id=run_id, error=error, on_complete=on_complete)

    _launch_background_thread(
        thread_name=f"research-run-confirm-{run_id}",
        target=background_worker,
    )


def continue_research_run_background(
    run_id: UUID,
    on_complete: Callable[[UUID, ResearchRunResult | None, str | None], None],
) -> None:
    """Resume a checkpointed run on a daemon thread and invoke on_complete when finished."""
    settings = Configuration()

    def background_worker() -> None:
        try:
            result: ResearchRunResult | None = execute_graph(
                settings=settings,
                run_id=run_id,
                initial_state=None,
            )
            if result is None:
                tracked_status: RunLifecycleStatus | None = get_run_status(run_id=run_id)
                if tracked_status == RunLifecycleStatus.FAILED:
                    raise RuntimeError(get_run_error(run_id=run_id) or "Research run failed.")
                if tracked_status == RunLifecycleStatus.AWAITING_INPUT:
                    on_complete(run_id, None, None)
                    return
                raise RuntimeError("Research stopped before completion.")
            on_complete(run_id, result, None)
        except Exception as error:
            _fail_background_run(run_id=run_id, error=error, on_complete=on_complete)

    _launch_background_thread(
        thread_name=f"research-run-continue-{run_id}",
        target=background_worker,
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
    register_run_metadata(run_id=selected_run_id, company_name=request.company_name)

    def background_worker() -> None:
        try:
            result: ResearchRunResult | None = execute_graph(
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

    _launch_background_thread(
        thread_name=f"research-run-{selected_run_id}",
        target=background_worker,
    )
    return selected_run_id
