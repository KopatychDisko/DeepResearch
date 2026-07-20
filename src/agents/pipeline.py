"""Assemble the LangGraph research topology from identity through verdict."""

from __future__ import annotations

from langgraph.graph import START, StateGraph

from agents.graph_state import ResearchRunState
from agents.hh_vacancies.node import analyze_hh_vacancies_step
from agents.identity.node import (
    _should_skip_identity_resolution,
    resolve_identity_step,
)
from agents.merge.node import merge_timeline_step
from agents.structure_events.node import structure_events_step
from agents.supervisor.node import supervisor_step, supervisor_tools_step
from agents.verdict.node import generate_verdict_step

__all__ = [
    "_should_skip_identity_resolution",
    "build_research_graph",
]


def build_research_graph() -> StateGraph:
    """Wire identity → HH vacancies → supervisor loop → structure_events → merge → verdict nodes."""
    graph: StateGraph = StateGraph(ResearchRunState)
    graph.add_node("resolve_identity", resolve_identity_step)
    graph.add_node("analyze_hh_vacancies", analyze_hh_vacancies_step)
    graph.add_node("supervisor", supervisor_step)
    graph.add_node("supervisor_tools", supervisor_tools_step)
    graph.add_node("structure_events", structure_events_step)
    graph.add_node("merge_timeline", merge_timeline_step)
    graph.add_node("generate_verdict", generate_verdict_step)
    graph.add_edge(START, "resolve_identity")
    graph.add_edge("analyze_hh_vacancies", "supervisor")
    graph.add_edge("supervisor", "supervisor_tools")
    graph.add_edge("structure_events", "merge_timeline")
    graph.add_edge("merge_timeline", "generate_verdict")
    return graph
