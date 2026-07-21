"""Manual hh.ru employer search retry for completed runs."""

from __future__ import annotations

from uuid import UUID

from agents.configuration import Configuration
from agents.graph.state import (
    ResearchRunState,
    dump_hh_vacancy_analysis,
    load_company_identity,
    load_run_request,
)
from agents.hh_vacancies.analysis import build_hh_vacancy_analysis
from agents.hh_vacancies.client import HhApiClient
from agents.models import ResearchRunResult, RunLifecycleStatus
from backend.run.checkpointer import compiled_research_graph
from backend.run.context import build_checkpointer_context
from backend.run.state_mapping import state_to_result, status_from_state


def retry_hh_employer_search(run_id: UUID, employer_query: str) -> ResearchRunResult:
    """Re-run hh.ru employer search for a completed run using a manual query override."""
    settings = Configuration()
    execution_context = build_checkpointer_context(settings=settings, run_id=run_id)

    with compiled_research_graph(settings=settings) as compiled_graph:
        state_snapshot = compiled_graph.get_state(config=execution_context.run_config)
        if state_snapshot.values is None or not state_snapshot.values:
            raise LookupError(f"Run not found: {run_id}")
        state: ResearchRunState = state_snapshot.values
        status: RunLifecycleStatus = status_from_state(state=state)
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
        return state_to_result(state=updated_snapshot.values)
