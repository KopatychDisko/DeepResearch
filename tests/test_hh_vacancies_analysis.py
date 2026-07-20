"""Unit tests for hh.ru vacancy analysis orchestration (mocked client and LLM)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableConfig

from agents.configuration import Configuration
from agents.hh_vacancies.analysis import build_hh_vacancy_analysis
from agents.hh_vacancies.client import parse_employer_rating, parse_vacancy_item
from agents.models import (
    CompanyIdentity,
    HhEmployerRating,
    HhVacancyItem,
    HhVacancyStatus,
    StructuredHhVacancyAssessment,
)

CANONICAL_NAME: str = "Яндекс"
USER_AGENT: str = "EmployerDD/1.0 (test@example.com)"


def _identity() -> CompanyIdentity:
    return CompanyIdentity(
        query_name=CANONICAL_NAME,
        canonical_name=CANONICAL_NAME,
        normalized_name="яндекс",
        company_url=None,
        profile_summary=None,
        user_description=None,
    )


def _settings() -> Configuration:
    return Configuration(hh_api_user_agent=USER_AGENT)


def _run_config() -> RunnableConfig:
    return {"configurable": {"thread_id": "test-thread"}}


def _sample_vacancy(vacancy_id: str, title: str) -> HhVacancyItem:
    return parse_vacancy_item(
        {
            "id": vacancy_id,
            "name": title,
            "alternate_url": f"https://hh.ru/vacancy/{vacancy_id}",
            "area": {"name": "Москва"},
            "salary": {"from": 200000, "to": 300000, "currency": "RUR", "gross": True},
            "employment": {"name": "Полная занятость"},
            "schedule": {"name": "Удаленная работа"},
            "experience": {"name": "От 3 до 6 лет"},
            "working_days": [{"name": "5/2"}],
            "working_time_modes": [{"name": "Полный день"}],
            "published_at": "2026-07-15T10:00:00+0300",
        }
    )


def _sample_rating() -> HhEmployerRating:
    return parse_employer_rating(
        {
            "alternate_url": "https://hh.ru/employer/1740",
            "trusted": True,
            "accredited_it_employer": True,
            "employer_rating": {
                "total_rating": 4.2,
                "reviews_count": 1284,
                "recommendation_percent": 87.5,
            },
        }
    )


def _mock_client(
    *,
    search_result: tuple[str, str] | None,
    rating: HhEmployerRating | None,
    vacancies: list[HhVacancyItem],
) -> MagicMock:
    client = MagicMock()
    client.search_employer_by_name.return_value = search_result
    client.fetch_employer_profile.return_value = rating
    client.fetch_active_vacancies.return_value = vacancies
    return client


def test_not_found_returns_empty_vacancies_and_explicit_message() -> None:
    client = _mock_client(search_result=None, rating=None, vacancies=[])

    analysis = build_hh_vacancy_analysis(
        identity=_identity(),
        settings=_settings(),
        client=client,
        config=_run_config(),
    )

    assert analysis.status == HhVacancyStatus.NOT_FOUND
    assert analysis.vacancies == []
    assert analysis.employer is None
    assert CANONICAL_NAME in analysis.message
    assert analysis.salary_summary == ""
    assert analysis.conditions_summary == ""


def test_found_path_calls_invoke_structured_output_when_vacancies_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vacancies = [_sample_vacancy("10000001", "Python-разработчик")]
    client = _mock_client(
        search_result=("1740", CANONICAL_NAME),
        rating=_sample_rating(),
        vacancies=vacancies,
    )
    invoke_calls: list[dict[str, Any]] = []

    def _fake_invoke_structured_output(
        config: RunnableConfig,
        model_class: type[StructuredHhVacancyAssessment],
        prompt: str,
    ) -> StructuredHhVacancyAssessment:
        invoke_calls.append(
            {
                "config": config,
                "model_class": model_class,
                "prompt": prompt,
            }
        )
        return StructuredHhVacancyAssessment(
            salary_summary="Salaries range from 200k to 300k RUR.",
            conditions_summary="Most roles offer remote work and full-time employment.",
            employer_rating_text="Employer rating on hh.ru: 4.2/5.",
        )

    monkeypatch.setattr(
        "agents.hh_vacancies.analysis.invoke_structured_output",
        _fake_invoke_structured_output,
    )

    analysis = build_hh_vacancy_analysis(
        identity=_identity(),
        settings=_settings(),
        client=client,
        config=_run_config(),
    )

    assert analysis.status == HhVacancyStatus.FOUND
    assert len(analysis.vacancies) == 1
    assert len(invoke_calls) == 1
    assert invoke_calls[0]["model_class"] is StructuredHhVacancyAssessment
    assert "10000001" in invoke_calls[0]["prompt"]
    assert analysis.salary_summary == "Salaries range from 200k to 300k RUR."
    assert "Employer rating on hh.ru: 4.2/5." in analysis.conditions_summary


def test_zero_vacancies_found_uses_rule_based_summaries_without_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _mock_client(
        search_result=("1740", CANONICAL_NAME),
        rating=_sample_rating(),
        vacancies=[],
    )
    invoke_called = False

    def _fail_invoke(*_args: object, **_kwargs: object) -> StructuredHhVacancyAssessment:
        nonlocal invoke_called
        invoke_called = True
        raise AssertionError("invoke_structured_output must not run without vacancies")

    monkeypatch.setattr(
        "agents.hh_vacancies.analysis.invoke_structured_output",
        _fail_invoke,
    )

    analysis = build_hh_vacancy_analysis(
        identity=_identity(),
        settings=_settings(),
        client=client,
        config=_run_config(),
    )

    assert analysis.status == HhVacancyStatus.FOUND
    assert analysis.vacancies == []
    assert invoke_called is False
    assert "No active vacancies" in analysis.salary_summary
    assert "4.2/5" in analysis.conditions_summary


def test_found_path_never_returns_more_than_ten_vacancies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    twelve_vacancies = [_sample_vacancy(str(10000000 + index), f"Role {index}") for index in range(12)]
    client = _mock_client(
        search_result=("1740", CANONICAL_NAME),
        rating=_sample_rating(),
        vacancies=twelve_vacancies[:10],
    )

    def _fake_invoke_structured_output(
        config: RunnableConfig,
        model_class: type[StructuredHhVacancyAssessment],
        prompt: str,
    ) -> StructuredHhVacancyAssessment:
        return StructuredHhVacancyAssessment(
            salary_summary="Salary spread across listed vacancies.",
            conditions_summary="Mixed remote and office schedules.",
            employer_rating_text="Employer rating on hh.ru: 4.2/5.",
        )

    monkeypatch.setattr(
        "agents.hh_vacancies.analysis.invoke_structured_output",
        _fake_invoke_structured_output,
    )

    analysis = build_hh_vacancy_analysis(
        identity=_identity(),
        settings=_settings(),
        client=client,
        config=_run_config(),
    )

    assert analysis.status == HhVacancyStatus.FOUND
    assert len(analysis.vacancies) <= 10
    client.fetch_active_vacancies.assert_called_once_with("1740", 10)


def test_unavailable_rating_uses_explicit_text_without_invented_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unavailable_rating = HhEmployerRating(
        available=False,
        average_score=None,
        reviews_count=None,
        recommendation_percent=None,
        trusted=True,
        accredited_it_employer=None,
        source_url="https://hh.ru/employer/1740",
    )
    vacancies = [_sample_vacancy("10000001", "Python-разработчик")]
    client = _mock_client(
        search_result=("1740", CANONICAL_NAME),
        rating=unavailable_rating,
        vacancies=vacancies,
    )

    def _fake_invoke_structured_output(
        config: RunnableConfig,
        model_class: type[StructuredHhVacancyAssessment],
        prompt: str,
    ) -> StructuredHhVacancyAssessment:
        return StructuredHhVacancyAssessment(
            salary_summary="Salaries vary by role.",
            conditions_summary="Remote-friendly schedules are common.",
            employer_rating_text="Employer rating on hh.ru is unavailable.",
        )

    monkeypatch.setattr(
        "agents.hh_vacancies.analysis.invoke_structured_output",
        _fake_invoke_structured_output,
    )

    analysis = build_hh_vacancy_analysis(
        identity=_identity(),
        settings=_settings(),
        client=client,
        config=_run_config(),
    )

    assert analysis.employer is not None
    assert analysis.employer.rating.available is False
    assert "unavailable" in analysis.conditions_summary.lower()


def test_error_path_returns_error_status_with_empty_vacancies() -> None:
    client = MagicMock()
    client.search_employer_by_name.side_effect = RuntimeError("HH API unavailable")

    analysis = build_hh_vacancy_analysis(
        identity=_identity(),
        settings=_settings(),
        client=client,
        config=_run_config(),
    )

    assert analysis.status == HhVacancyStatus.ERROR
    assert analysis.vacancies == []
    assert "HH API unavailable" in analysis.message
