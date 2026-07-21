"""Tests for identity-confirm resume routing through analyze_hh_vacancies."""

from __future__ import annotations

from uuid import uuid4

from langgraph.types import Command

from agents.graph.state import dump_company_identity, dump_hh_vacancy_analysis
from agents.hh_vacancies.analysis import build_pending_hh_vacancy_analysis
from agents.identity.resolution import candidate_to_identity
from agents.models import (
    CompanyCandidate,
    Confidence,
    HhVacancyAnalysis,
    HhVacancyStatus,
    RunLifecycleStatus,
    RunPhase,
    RunRequest,
)
from backend.run.execution import graph_resume_input
from backend.run.initial_state import build_initial_state
from backend.run.state_mapping import hh_vacancy_analysis_pending


def _confirmed_identity_state(*, hh_analysis: HhVacancyAnalysis) -> dict[str, object]:
    run_id = uuid4()
    request = RunRequest(company_name="Яндекс")
    state = build_initial_state(request=request, run_id=run_id)
    candidate = CompanyCandidate(
        candidate_id="abc123",
        name="Яндекс",
        description="IT company",
        website_url="https://yandex.ru",
        confidence=Confidence.HIGH,
    )
    state["status"] = RunLifecycleStatus.RUNNING.value
    state["phase"] = RunPhase.ANALYZE_HH_VACANCIES.value
    state["identity_candidates"] = []
    state["identity"] = dump_company_identity(
        candidate_to_identity(
            candidate=candidate,
            query_name=request.company_name,
            requested_company_url=None,
            user_description=None,
        )
    )
    state["hh_vacancy_analysis"] = dump_hh_vacancy_analysis(hh_analysis)
    return state


def _completed_hh_analysis() -> HhVacancyAnalysis:
    return HhVacancyAnalysis(
        status=HhVacancyStatus.NOT_FOUND,
        message="Employer not found on hh.ru for canonical name «Яндекс».",
        search_query="Яндекс",
        employer=None,
        vacancies=[],
        salary_summary="",
        conditions_summary="",
        fetched_at="2026-07-20T10:00:00+00:00",
    )


def test_hh_vacancy_analysis_pending_for_initial_placeholder() -> None:
    run_id = uuid4()
    request = RunRequest(company_name="Яндекс")
    state = build_initial_state(request=request, run_id=run_id)

    assert hh_vacancy_analysis_pending(state=state) is True


def test_hh_vacancy_analysis_not_pending_after_fetch() -> None:
    state = _confirmed_identity_state(hh_analysis=_completed_hh_analysis())

    assert hh_vacancy_analysis_pending(state=state) is False


def test_graph_resume_input_routes_to_analyze_hh_vacancies_when_pending() -> None:
    pending = build_pending_hh_vacancy_analysis(search_query="Яндекс")
    state = _confirmed_identity_state(hh_analysis=pending)

    resume_input = graph_resume_input(state=state, next_nodes=())

    assert resume_input is not None
    assert isinstance(resume_input, Command)
    assert resume_input.goto == "analyze_hh_vacancies"


def test_graph_resume_input_routes_to_supervisor_when_hh_complete() -> None:
    state = _confirmed_identity_state(hh_analysis=_completed_hh_analysis())

    resume_input = graph_resume_input(state=state, next_nodes=())

    assert resume_input is not None
    assert isinstance(resume_input, Command)
    assert resume_input.goto == "supervisor"
