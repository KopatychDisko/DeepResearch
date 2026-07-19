"""Graph node that merges structured events into a canonical timeline."""

from __future__ import annotations

from typing import Literal

from langgraph.types import Command

from agents.graph_state import ResearchRunState, dump_canonical_timeline, load_company_events
from agents.merge.merge import merge_events_into_timeline
from agents.models import RunPhase


def _phase_update(phase: RunPhase) -> dict[str, str]:
    return {"phase": phase.value}


def merge_timeline_step(state: ResearchRunState) -> Command[Literal["generate_verdict"]]:
    """Deduplicate events into a canonical timeline, then continue to verdict."""
    events = load_company_events(state["events"])
    timeline = merge_events_into_timeline(events)
    return Command(
        goto="generate_verdict",
        update={
            "timeline": dump_canonical_timeline(timeline),
            **_phase_update(RunPhase.MERGE_TIMELINE),
        },
    )
