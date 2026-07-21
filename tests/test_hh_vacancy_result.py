"""Integration tests for hh_vacancy_analysis in ResearchRunResult assembly."""

from __future__ import annotations

from uuid import uuid4

from agents.graph.state import (
    dump_canonical_timeline,
    dump_company_identity,
    dump_employer_verdict,
    dump_hh_vacancy_analysis,
    dump_run_request,
)
from agents.models import (
    CanonicalTimeline,
    CompanyIdentity,
    HhVacancyAnalysis,
    HhVacancyStatus,
    RunLifecycleStatus,
    RunPhase,
    RunRequest,
    RunStatusResponse,
)
from agents.verdict.verdict import build_insufficient_data_verdict
from backend.run.initial_state import build_initial_state
from backend.run.state_mapping import state_to_result
from backend.run.status import build_status_response
from agents.hh_vacancies.analysis import build_pending_hh_vacancy_analysis


def _minimal_completed_state(
    hh_analysis: HhVacancyAnalysis,
) -> dict[str, object]:
    request = RunRequest(company_name="Яндекс")
    identity = CompanyIdentity(
        query_name="Яндекс",
        canonical_name="Яндекс",
        normalized_name="яндекс",
        company_url=None,
        profile_summary=None,
        user_description=None,
    )
    return {
        "run_id": str(uuid4()),
        "phase": RunPhase.COMPLETED.value,
        "status": RunLifecycleStatus.COMPLETED.value,
        "error_message": None,
        "request": dump_run_request(request),
        "identity": dump_company_identity(identity),
        "hh_vacancy_analysis": dump_hh_vacancy_analysis(hh_analysis),
        "findings": [],
        "events": [],
        "timeline": dump_canonical_timeline(CanonicalTimeline(events=[], conflicts=[])),
        "verdict": dump_employer_verdict(
            build_insufficient_data_verdict(
                company_name="Яндекс",
                language=request.response_language,
            )
        ),
        "identity_candidates": [],
        "completed_sources": [],
        "conversation_history": [],
        "iteration_count": 0,
        "finished": True,
        "budget_deadline_unix": None,
        "estimated_tokens_used": 0,
        "budget_stop_reason": None,
    }


def _not_found_analysis() -> HhVacancyAnalysis:
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


def _found_analysis() -> HhVacancyAnalysis:
    return HhVacancyAnalysis(
        status=HhVacancyStatus.FOUND,
        message="Found 2 active vacancies on hh.ru for «Яндекс».",
        search_query="Яндекс",
        employer=None,
        vacancies=[],
        salary_summary="150 000 – 220 000 ₽ typical range.",
        conditions_summary="Hybrid and remote schedules common.",
        fetched_at="2026-07-20T10:00:00+00:00",
    )


def test_build_initial_state_seeds_pending_hh_vacancy_analysis() -> None:
    run_id = uuid4()
    request = RunRequest(company_name="Яндекс")
    state = build_initial_state(request=request, run_id=run_id)

    assert "hh_vacancy_analysis" in state
    pending = HhVacancyAnalysis.model_validate(state["hh_vacancy_analysis"])
    assert pending.status == HhVacancyStatus.NOT_FOUND
    assert pending.vacancies == []
    assert pending.fetched_at == ""


def test_state_to_result_includes_not_found_hh_vacancy_analysis() -> None:
    state = _minimal_completed_state(_not_found_analysis())
    result = state_to_result(state=state)

    assert result.hh_vacancy_analysis.status == HhVacancyStatus.NOT_FOUND
    assert result.hh_vacancy_analysis.vacancies == []
    assert "Employer not found" in result.hh_vacancy_analysis.message


def test_state_to_result_includes_found_hh_vacancy_analysis() -> None:
    state = _minimal_completed_state(_found_analysis())
    result = state_to_result(state=state)

    assert result.hh_vacancy_analysis.status == HhVacancyStatus.FOUND
    assert result.hh_vacancy_analysis.salary_summary != ""
    assert result.hh_vacancy_analysis.conditions_summary != ""


def test_research_run_result_verdict_fields_unchanged() -> None:
    state = _minimal_completed_state(_found_analysis())
    result = state_to_result(state=state)

    assert result.verdict.score >= 1
    assert result.verdict.summary != ""
    assert result.identity.canonical_name == "Яндекс"


def test_build_status_response_serializes_hh_vacancy_analysis() -> None:
    run_id = uuid4()
    state = _minimal_completed_state(_not_found_analysis())
    response = build_status_response(run_id=run_id, state=state, next_nodes=())

    assert response.result is not None
    dumped = response.model_dump(mode="json")
    hh_payload = dumped["result"]["hh_vacancy_analysis"]
    assert hh_payload["status"] == "not_found"
    assert hh_payload["vacancies"] == []
    assert "message" in hh_payload


def test_build_pending_hh_vacancy_analysis_is_not_yet_fetched() -> None:
    pending = build_pending_hh_vacancy_analysis(search_query="Яндекс")
    assert pending.status == HhVacancyStatus.NOT_FOUND
    assert pending.fetched_at == ""
    assert pending.vacancies == []
