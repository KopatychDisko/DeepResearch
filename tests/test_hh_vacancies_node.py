"""Unit tests for the analyze_hh_vacancies graph node."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from agents.graph.state import (
    ResearchRunState,
    dump_company_identity,
    dump_run_request,
    load_hh_vacancy_analysis,
)
from agents.hh_vacancies.node import analyze_hh_vacancies_step
from agents.models import (
    CompanyIdentity,
    HhVacancyAnalysis,
    HhVacancyStatus,
    RunPhase,
    RunRequest,
)


def _run_config() -> RunnableConfig:
    return {"configurable": {"thread_id": "test-thread"}}


def _state() -> ResearchRunState:
    request = RunRequest(company_name="Яндекс", company_url=None, company_description=None)
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
        "phase": RunPhase.RESOLVE_IDENTITY.value,
        "status": "running",
        "error_message": None,
        "request": dump_run_request(request),
        "identity": dump_company_identity(identity),
        "hh_vacancy_analysis": {},
        "findings": [],
        "events": [],
        "timeline": {"events": [], "conflicts": []},
        "verdict": {},
        "identity_candidates": [],
        "completed_sources": [],
        "conversation_history": [],
        "iteration_count": 0,
        "finished": False,
        "budget_deadline_unix": None,
        "estimated_tokens_used": 0,
        "budget_stop_reason": None,
    }


def _found_analysis() -> HhVacancyAnalysis:
    return HhVacancyAnalysis(
        status=HhVacancyStatus.FOUND,
        message="Found 2 active vacancies on hh.ru for «Яндекс».",
        search_query="Яндекс",
        employer=None,
        vacancies=[],
        salary_summary="Salaries vary.",
        conditions_summary="Remote-friendly roles.",
        fetched_at="2026-07-20T10:00:00+00:00",
    )


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


def test_analyze_hh_vacancies_step_routes_to_supervisor_with_found_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_calls: list[dict[str, Any]] = []

    def _fake_build_hh_vacancy_analysis(*args: object, **kwargs: object) -> HhVacancyAnalysis:
        captured_calls.append({"args": args, "kwargs": kwargs})
        return _found_analysis()

    monkeypatch.setattr(
        "agents.hh_vacancies.node.build_hh_vacancy_analysis",
        _fake_build_hh_vacancy_analysis,
    )
    monkeypatch.setattr(
        "agents.hh_vacancies.node.HhApiClient",
        lambda settings: type("Client", (), {"close": lambda self: None})(),
    )

    command = analyze_hh_vacancies_step(state=_state(), config=_run_config())

    assert isinstance(command, Command)
    assert command.goto == "supervisor"
    assert command.update is not None
    assert command.update["phase"] == RunPhase.ANALYZE_HH_VACANCIES.value
    loaded = load_hh_vacancy_analysis(command.update["hh_vacancy_analysis"])
    assert loaded.status == HhVacancyStatus.FOUND
    assert len(captured_calls) == 1


def test_analyze_hh_vacancies_step_persists_not_found_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agents.hh_vacancies.node.build_hh_vacancy_analysis",
        lambda *args, **kwargs: _not_found_analysis(),
    )
    monkeypatch.setattr(
        "agents.hh_vacancies.node.HhApiClient",
        lambda settings: type("Client", (), {"close": lambda self: None})(),
    )

    command = analyze_hh_vacancies_step(state=_state(), config=_run_config())

    assert command.goto == "supervisor"
    assert command.update is not None
    loaded = load_hh_vacancy_analysis(command.update["hh_vacancy_analysis"])
    assert loaded.status == HhVacancyStatus.NOT_FOUND
    assert loaded.vacancies == []
    assert loaded.message != ""
