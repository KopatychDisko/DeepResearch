"""Graph node that generates the final employer verdict and completes the run."""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from agents.graph.state import (
    ResearchRunState,
    dump_employer_verdict,
    load_canonical_timeline,
    load_company_identity,
    load_run_request,
)
from agents.models import RunLifecycleStatus, RunPhase
from agents.verdict.verdict import generate_employer_verdict


def _phase_update(phase: RunPhase) -> dict[str, str]:
    return {"phase": phase.value}


def generate_verdict_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["__end__"]]:
    """Produce the employer verdict from the timeline and end the research run."""
    identity = load_company_identity(state["identity"])
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
