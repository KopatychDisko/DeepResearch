"""Graph node that analyzes hh.ru vacancies after identity resolution."""

from __future__ import annotations

from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from agents.configuration import Configuration
from agents.graph.state import (
    ResearchRunState,
    dump_hh_vacancy_analysis,
    load_company_identity,
    load_run_request,
)
from agents.hh_vacancies.analysis import build_hh_vacancy_analysis
from agents.hh_vacancies.client import HhApiClient
from agents.models import RunPhase


def _phase_update(phase: RunPhase) -> dict[str, str]:
    return {"phase": phase.value}


def analyze_hh_vacancies_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["supervisor"]]:
    """Fetch hh.ru vacancy analysis for the resolved identity, then continue to supervisor."""
    settings: Configuration = Configuration.from_runnable_config(config)
    client: HhApiClient = HhApiClient(settings)

    try:
        identity = load_company_identity(state["identity"])
        request = load_run_request(state["request"])

        analysis = build_hh_vacancy_analysis(
            identity=identity,
            settings=settings,
            client=client,
            config=config,
            search_query_override=None,
            response_language=request.response_language,
        )
    finally:
        client.close()

    return Command(
        goto="supervisor",
        update={
            "hh_vacancy_analysis": dump_hh_vacancy_analysis(analysis),
            **_phase_update(RunPhase.ANALYZE_HH_VACANCIES),
        },
    )
