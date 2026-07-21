"""Map checkpoint state to API result and lifecycle enums."""

from __future__ import annotations

from agents.graph.state import (
    ResearchRunState,
    load_canonical_timeline,
    load_company_events,
    load_company_identity,
    load_employer_verdict,
    load_hh_vacancy_analysis,
    load_raw_findings,
    is_hh_vacancy_analysis_pending,
)
from agents.models import ResearchRunResult, RunLifecycleStatus, RunPhase


def state_to_result(state: ResearchRunState) -> ResearchRunResult:
    """Convert a completed checkpoint state into a ResearchRunResult."""
    return ResearchRunResult(
        identity=load_company_identity(state["identity"]),
        findings=load_raw_findings(state["findings"]),
        events=load_company_events(state["events"]),
        timeline=load_canonical_timeline(state["timeline"]),
        verdict=load_employer_verdict(state["verdict"]),
        hh_vacancy_analysis=load_hh_vacancy_analysis(state["hh_vacancy_analysis"]),
    )


def phase_from_state(state: ResearchRunState) -> RunPhase:
    """Parse the run phase enum from checkpoint state."""
    phase_value: object = state.get("phase", RunPhase.PENDING.value)
    if not isinstance(phase_value, str) or phase_value.strip() == "":
        return RunPhase.PENDING
    try:
        return RunPhase(phase_value)
    except ValueError:
        return RunPhase.PENDING


def status_from_state(state: ResearchRunState) -> RunLifecycleStatus:
    """Parse the lifecycle status enum from checkpoint state."""
    status_value: object = state.get("status", RunLifecycleStatus.RUNNING.value)
    if not isinstance(status_value, str) or status_value.strip() == "":
        return RunLifecycleStatus.RUNNING
    try:
        return RunLifecycleStatus(status_value)
    except ValueError:
        return RunLifecycleStatus.RUNNING


def hh_vacancy_analysis_pending(state: ResearchRunState) -> bool:
    """Return True when HH analysis has not yet been fetched for this run."""
    return is_hh_vacancy_analysis_pending(state=state)
