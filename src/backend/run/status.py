"""Build run status responses for polling clients."""

from __future__ import annotations

from uuid import UUID

from agents.graph.state import (
    ResearchRunState,
    load_company_candidates,
    load_company_identity,
    load_completed_sources,
)
from agents.models import ResearchRunResult, RunLifecycleStatus, RunPhase, RunStatusResponse, utc_now
from backend.run.registry import get_run_company_name, get_run_error, get_run_status
from backend.run.state_mapping import phase_from_state, state_to_result, status_from_state

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


def checkpoint_ready_for_status(state: dict[str, object]) -> bool:
    """Return True when checkpoint state has all keys required for a full status response."""
    return all(key in state for key in _STATUS_REQUIRED_KEYS)


def tracked_status_response(run_id: UUID) -> RunStatusResponse:
    """Return a minimal status response from in-memory registry when checkpoint is not ready."""
    tracked_status: RunLifecycleStatus | None = get_run_status(run_id=run_id)
    if tracked_status is None:
        raise LookupError(f"Run not found: {run_id}")
    return RunStatusResponse(
        run_id=run_id,
        created_at=utc_now(),
        status=tracked_status,
        phase=RunPhase.PENDING,
        company_name=get_run_company_name(run_id=run_id),
        completed_sources=[],
        findings_count=0,
        events_count=0,
        iteration_count=0,
        error_message=get_run_error(run_id=run_id),
        identity_candidates=[],
        result=None,
    )


def build_status_response(
    run_id: UUID,
    state: ResearchRunState,
    next_nodes: tuple[str, ...],
) -> RunStatusResponse:
    """Build a full status response from checkpoint state."""
    _ = next_nodes
    if not checkpoint_ready_for_status(state=dict(state)):
        return tracked_status_response(run_id=run_id)

    phase: RunPhase = phase_from_state(state=state)
    status: RunLifecycleStatus = status_from_state(state=state)
    result: ResearchRunResult | None = None
    if status == RunLifecycleStatus.COMPLETED:
        phase = RunPhase.COMPLETED
        result = state_to_result(state=state)
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
