"""Graph node that resolves company identity before the supervisor research loop."""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from agents.configuration import Configuration
from agents.graph_state import (
    ResearchRunState,
    dump_company_candidates,
    dump_company_identity,
    load_run_request,
)
from agents.identity.resolution import (
    IdentityResolutionStatus,
    resolve_company_identity_from_web,
)
from agents.models import RunLifecycleStatus, RunPhase


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
) -> Command[Literal["supervisor", "analyze_hh_vacancies", "__end__"]]:
    """Confirm company identity or end the run when resolution fails or is ambiguous."""
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
        goto="analyze_hh_vacancies",
        update={
            "identity": dump_company_identity(resolution.identity),
            "identity_candidates": dump_company_candidates(resolution.candidates),
            **_phase_update(RunPhase.RESOLVE_IDENTITY),
        },
    )
