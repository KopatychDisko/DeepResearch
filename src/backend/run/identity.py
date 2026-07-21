"""Identity confirmation against checkpointed runs."""

from __future__ import annotations

from uuid import UUID

from agents.configuration import Configuration
from agents.graph.state import (
    ResearchRunState,
    dump_company_identity,
    load_company_candidates,
    load_run_request,
)
from agents.identity.resolution import candidate_to_identity, find_candidate_by_id
from agents.models import RunLifecycleStatus, RunPhase, RunRequest
from backend.run.checkpointer import compiled_research_graph
from backend.run.context import RunExecutionContext, build_checkpointer_context
from backend.run.registry import set_run_status
from backend.run.state_mapping import status_from_state


def require_awaiting_identity_confirmation(state: ResearchRunState, run_id: UUID) -> None:
    """Raise when the run is not waiting for identity confirmation."""
    status: RunLifecycleStatus = status_from_state(state=state)
    if status != RunLifecycleStatus.AWAITING_INPUT:
        raise ValueError(f"Run {run_id} is not awaiting identity confirmation.")


def load_checkpoint_state(run_id: UUID) -> tuple[Configuration, RunExecutionContext, ResearchRunState]:
    """Load checkpoint state for a run or raise LookupError when missing."""
    settings = Configuration()
    execution_context = build_checkpointer_context(settings=settings, run_id=run_id)
    with compiled_research_graph(settings=settings) as compiled_graph:
        state_snapshot = compiled_graph.get_state(config=execution_context.run_config)
        if state_snapshot.values is None or not state_snapshot.values:
            raise LookupError(f"Run not found: {run_id}")
        state: ResearchRunState = state_snapshot.values
    return settings, execution_context, state


def validate_identity_confirmation_request(run_id: UUID, candidate_id: str) -> None:
    """Ensure the run awaits identity input and that candidate_id exists among candidates."""
    _settings, _execution_context, state = load_checkpoint_state(run_id=run_id)
    require_awaiting_identity_confirmation(state=state, run_id=run_id)
    candidates = load_company_candidates(state.get("identity_candidates", []))
    find_candidate_by_id(candidates=candidates, candidate_id=candidate_id)


def confirm_company_identity_selection(run_id: UUID, candidate_id: str) -> RunRequest:
    """Persist the selected candidate as identity and clear the awaiting-input interrupt."""
    settings, execution_context, state = load_checkpoint_state(run_id=run_id)
    require_awaiting_identity_confirmation(state=state, run_id=run_id)

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

    with compiled_research_graph(settings=settings) as compiled_graph:
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
    set_run_status(run_id=run_id, status=RunLifecycleStatus.RUNNING, error_message=None)
    return request
