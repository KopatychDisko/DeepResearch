from __future__ import annotations

import os
from contextlib import ExitStack
from typing import NotRequired, TypedDict
from unittest.mock import MagicMock, patch

from langchain_core.runnables import RunnableConfig

from agents.configuration import Configuration
from agents.hh_vacancies.analysis import build_hh_vacancy_analysis
from agents.hh_vacancies.client import parse_employer_rating, parse_vacancy_item
from agents.models import (
    CompanyIdentity,
    HhEmployerRating,
    HhVacancyAnalysis,
    HhVacancyItem,
    ResponseLanguage,
    StructuredHhVacancyAssessment,
)
from tests.eval_common import load_golden_dataset

HH_EVAL_USER_AGENT: str = "EmployerDD/1.0 (test@example.com)"
HH_API_USER_AGENT_ENV: str = "HH_API_USER_AGENT"
MAX_ACTIVE_VACANCIES: int = 10


class HhAnalysisGoldenCase(TypedDict):
    id: str
    canonical_name: str
    mock_search_result: list[str] | None
    mock_vacancies: list[dict[str, object]]
    mock_rating: dict[str, object] | None
    response_language: str
    expected_status: str
    expected_vacancy_count: int
    invoke_llm: bool
    message_contains: NotRequired[list[str]]
    salary_summary_contains: NotRequired[list[str]]
    conditions_summary_contains: NotRequired[list[str]]
    client_raises: NotRequired[str]
    missing_user_agent: NotRequired[bool]
    llm_salary_summary: NotRequired[str]
    llm_conditions_summary: NotRequired[str]
    llm_employer_rating_text: NotRequired[str]


def load_hh_analysis_golden_cases() -> list[HhAnalysisGoldenCase]:
    raw_cases: list[dict[str, object]] = load_golden_dataset("hh_analysis_golden")
    typed_cases: list[HhAnalysisGoldenCase] = []
    for raw_case in raw_cases:
        if "id" not in raw_case or not isinstance(raw_case["id"], str):
            raise TypeError("Each HH analysis golden case must have a string id")
        typed_cases.append(raw_case)  # type: ignore[arg-type]
    return typed_cases


def build_identity_from_case(case: HhAnalysisGoldenCase) -> CompanyIdentity:
    canonical_name: str = case["canonical_name"]
    return CompanyIdentity(
        query_name=canonical_name,
        canonical_name=canonical_name,
        normalized_name=canonical_name.casefold(),
        company_url=None,
        profile_summary=None,
        user_description=None,
    )


def _parse_rating_from_case(case: HhAnalysisGoldenCase) -> HhEmployerRating | None:
    mock_rating: dict[str, object] | None = case["mock_rating"]
    if mock_rating is None:
        return None
    return parse_employer_rating(mock_rating)


def _parse_vacancies_from_case(case: HhAnalysisGoldenCase) -> list[HhVacancyItem]:
    vacancies: list[HhVacancyItem] = []
    for vacancy_payload in case["mock_vacancies"]:
        vacancies.append(parse_vacancy_item(vacancy_payload))
    return vacancies


def _mock_client_from_golden(case: HhAnalysisGoldenCase) -> MagicMock:
    client: MagicMock = MagicMock()
    client_raises: str | None = case.get("client_raises")
    if client_raises is not None:

        def _raise_on_search(search_text: str) -> list[dict[str, object]]:
            _ = search_text
            raise RuntimeError(client_raises)

        client.collect_employer_candidates.side_effect = _raise_on_search
        return client

    mock_search_result: list[str] | None = case["mock_search_result"]
    rating: HhEmployerRating | None = _parse_rating_from_case(case=case)
    vacancies: list[HhVacancyItem] = _parse_vacancies_from_case(case=case)

    def _list_employer_search_items(search_text: str) -> list[dict[str, object]]:
        _ = search_text
        if mock_search_result is None:
            return []
        employer_id: str = mock_search_result[0]
        employer_name: str = mock_search_result[1]
        return [{"id": employer_id, "name": employer_name}]

    client.collect_employer_candidates.side_effect = _list_employer_search_items
    client.fetch_employer_profile.return_value = rating
    client.fetch_enriched_active_vacancies.return_value = vacancies
    return client


def _run_config() -> RunnableConfig:
    return {"configurable": {"thread_id": "hh-eval-thread"}}


def _build_settings(case: HhAnalysisGoldenCase) -> Configuration:
    if case.get("missing_user_agent"):
        return Configuration(hh_api_user_agent="EmployerDD/1.0 (contact@example.com)")
    return Configuration(hh_api_user_agent=HH_EVAL_USER_AGENT)


def _configure_user_agent_env(case: HhAnalysisGoldenCase) -> None:
    if case.get("missing_user_agent"):
        os.environ.pop(HH_API_USER_AGENT_ENV, None)
        return
    os.environ[HH_API_USER_AGENT_ENV] = HH_EVAL_USER_AGENT


def _build_fake_invoke(case: HhAnalysisGoldenCase):
    def _fake_invoke_structured_output(
        config: RunnableConfig,
        model_class: type[StructuredHhVacancyAssessment],
        prompt: str,
    ) -> StructuredHhVacancyAssessment:
        _ = config
        _ = model_class
        _ = prompt
        salary_summary: str = case.get("llm_salary_summary", "Mock salary summary.")
        conditions_summary: str = case.get("llm_conditions_summary", "Mock conditions summary.")
        employer_rating_text: str = case.get(
            "llm_employer_rating_text",
            "Employer rating on hh.ru: 4.2/5.",
        )
        return StructuredHhVacancyAssessment(
            salary_summary=salary_summary,
            conditions_summary=conditions_summary,
            employer_rating_text=employer_rating_text,
        )

    return _fake_invoke_structured_output


def _build_fail_invoke():
    def _fail_invoke(*_args: object, **_kwargs: object) -> StructuredHhVacancyAssessment:
        raise AssertionError("invoke_structured_output must not run for this golden case")

    return _fail_invoke


def run_hh_analysis(case: HhAnalysisGoldenCase) -> HhVacancyAnalysis:
    _configure_user_agent_env(case=case)
    client: MagicMock = _mock_client_from_golden(case=case)
    identity: CompanyIdentity = build_identity_from_case(case=case)
    settings: Configuration = _build_settings(case=case)
    response_language: ResponseLanguage = ResponseLanguage(case["response_language"])

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "agents.hh_vacancies.analysis._reformulate_hh_search_queries",
                return_value=[],
            )
        )
        if case["invoke_llm"]:
            stack.enter_context(
                patch(
                    "agents.hh_vacancies.analysis.invoke_structured_output",
                    side_effect=_build_fake_invoke(case=case),
                )
            )
        elif (
            case["expected_status"] == "found"
            and case["expected_vacancy_count"] == 0
            and not case["invoke_llm"]
        ):
            stack.enter_context(
                patch(
                    "agents.hh_vacancies.analysis.invoke_structured_output",
                    side_effect=_build_fail_invoke(),
                )
            )

        return build_hh_vacancy_analysis(
            identity=identity,
            settings=settings,
            client=client,
            config=_run_config(),
            search_query_override=None,
            response_language=response_language,
        )


def status_score(case: HhAnalysisGoldenCase, result: HhVacancyAnalysis) -> float:
    if result.status.value != case["expected_status"]:
        return 0.0
    message_contains: list[str] | None = case.get("message_contains")
    if message_contains is not None:
        for substring in message_contains:
            if substring not in result.message:
                return 0.0
    return 1.0


def vacancy_cap_score(case: HhAnalysisGoldenCase, result: HhVacancyAnalysis) -> float:
    vacancy_count: int = len(result.vacancies)
    if vacancy_count > MAX_ACTIVE_VACANCIES:
        return 0.0
    if vacancy_count != case["expected_vacancy_count"]:
        return 0.0
    return 1.0


def no_llm_when_empty_score(case: HhAnalysisGoldenCase, result: HhVacancyAnalysis) -> float:
    if case["invoke_llm"]:
        return 1.0
    if case["expected_vacancy_count"] != 0:
        return 1.0
    if case["expected_status"] != "found":
        return 1.0
    salary_summary_contains: list[str] | None = case.get("salary_summary_contains")
    if salary_summary_contains is None:
        return 1.0
    if result.salary_summary.strip() == "":
        return 0.0
    for substring in salary_summary_contains:
        if substring not in result.salary_summary:
            return 0.0
    conditions_summary_contains: list[str] | None = case.get("conditions_summary_contains")
    if conditions_summary_contains is not None:
        for substring in conditions_summary_contains:
            if substring not in result.conditions_summary:
                return 0.0
    return 1.0
