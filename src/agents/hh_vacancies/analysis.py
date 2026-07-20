"""Orchestrate hh.ru employer lookup, vacancy fetch, and structured LLM summaries."""

from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from agents.configuration import Configuration
from agents.hh_vacancies.client import HhApiClient
from agents.models import (
    CompanyIdentity,
    HhEmployerRating,
    HhVacancyAnalysis,
    HhVacancyItem,
    HhVacancyStatus,
    HhVacancySummary,
    StructuredHhVacancyAssessment,
)
from agents.structured_output import invoke_structured_output

MAX_ACTIVE_VACANCIES: int = 10


def build_pending_hh_vacancy_analysis(search_query: str) -> HhVacancyAnalysis:
    """Return the initial placeholder block before analyze_hh_vacancies runs."""
    return HhVacancyAnalysis(
        status=HhVacancyStatus.NOT_FOUND,
        message="",
        search_query=search_query,
        employer=None,
        vacancies=[],
        salary_summary="",
        conditions_summary="",
        fetched_at="",
    )


def _utc_now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def _unavailable_rating() -> HhEmployerRating:
    return HhEmployerRating(
        available=False,
        average_score=None,
        reviews_count=None,
        recommendation_percent=None,
        trusted=None,
        accredited_it_employer=None,
        source_url=None,
    )


def _build_employer_summary(
    employer_id: str,
    employer_name: str,
    rating: HhEmployerRating,
) -> HhVacancySummary:
    profile_url: str = (
        str(rating.source_url) if rating.source_url is not None else f"https://hh.ru/employer/{employer_id}"
    )
    return HhVacancySummary(
        employer_id=employer_id,
        name=employer_name,
        profile_url=profile_url,
        site_url=None,
        open_vacancies_count=None,
        rating=rating,
    )


def _rule_based_rating_text(rating: HhEmployerRating) -> str:
    if rating.available and rating.average_score is not None:
        return f"Employer rating on hh.ru: {rating.average_score}/5."
    return "Employer rating on hh.ru is unavailable."


def _rule_based_zero_vacancy_summaries(rating: HhEmployerRating) -> tuple[str, str]:
    rating_text: str = _rule_based_rating_text(rating)
    salary_summary: str = "No active vacancies are listed on hh.ru for this employer."
    conditions_summary: str = (
        f"{rating_text} No vacancy schedule or employment terms to summarize."
    )
    return salary_summary, conditions_summary


def _vacancies_json_prompt(vacancies: list[HhVacancyItem]) -> str:
    payload: list[dict[str, object]] = [
        vacancy.model_dump(mode="json") for vacancy in vacancies
    ]
    return json.dumps(payload, ensure_ascii=False)


def _llm_vacancy_prompt(
    identity: CompanyIdentity,
    vacancies: list[HhVacancyItem],
    rating: HhEmployerRating,
) -> str:
    return (
        f"Summarize hh.ru vacancy data for employer {identity.canonical_name}.\n"
        f"Employer rating available: {rating.available}\n"
        f"Vacancies JSON:\n{_vacancies_json_prompt(vacancies)}\n"
        "Produce concise salary range spread, typical working conditions, and employer "
        "rating text. When rating is unavailable, state that explicitly without inventing "
        "numeric scores."
    )


def _combine_conditions_summary(
    conditions_summary: str,
    employer_rating_text: str,
) -> str:
    if employer_rating_text in conditions_summary:
        return conditions_summary
    return f"{conditions_summary}\n\n{employer_rating_text}"


def build_hh_vacancy_analysis(
    identity: CompanyIdentity,
    settings: Configuration,
    client: HhApiClient,
    config: RunnableConfig,
) -> HhVacancyAnalysis:
    """Fetch hh.ru vacancies for identity.canonical_name and build a structured analysis block."""
    del settings
    fetched_at: str = _utc_now_iso()
    search_query: str = identity.canonical_name

    try:
        match = client.search_employer_by_name(search_query)
        if match is None:
            return HhVacancyAnalysis(
                status=HhVacancyStatus.NOT_FOUND,
                message=(
                    f"Employer not found on hh.ru for canonical name «{search_query}»."
                ),
                search_query=search_query,
                employer=None,
                vacancies=[],
                salary_summary="",
                conditions_summary="",
                fetched_at=fetched_at,
            )

        employer_id, employer_name = match
        rating: HhEmployerRating = client.fetch_employer_profile(employer_id)
        if rating is None:
            rating = _unavailable_rating()

        vacancies: list[HhVacancyItem] = client.fetch_active_vacancies(
            employer_id,
            MAX_ACTIVE_VACANCIES,
        )
        employer: HhVacancySummary = _build_employer_summary(
            employer_id=employer_id,
            employer_name=employer_name,
            rating=rating,
        )

        if vacancies:
            parsed_summary: StructuredHhVacancyAssessment = invoke_structured_output(
                config=config,
                model_class=StructuredHhVacancyAssessment,
                prompt=_llm_vacancy_prompt(
                    identity=identity,
                    vacancies=vacancies,
                    rating=rating,
                ),
            )
            salary_summary: str = parsed_summary.salary_summary
            conditions_summary: str = _combine_conditions_summary(
                conditions_summary=parsed_summary.conditions_summary,
                employer_rating_text=parsed_summary.employer_rating_text,
            )
        else:
            salary_summary, conditions_summary = _rule_based_zero_vacancy_summaries(
                rating=rating,
            )

        return HhVacancyAnalysis(
            status=HhVacancyStatus.FOUND,
            message=(
                f"Found {len(vacancies)} active vacancies on hh.ru for «{employer_name}»."
            ),
            search_query=search_query,
            employer=employer,
            vacancies=vacancies,
            salary_summary=salary_summary,
            conditions_summary=conditions_summary,
            fetched_at=fetched_at,
        )
    except Exception as error:
        return HhVacancyAnalysis(
            status=HhVacancyStatus.ERROR,
            message=f"HH vacancy analysis failed: {error}",
            search_query=search_query,
            employer=None,
            vacancies=[],
            salary_summary="",
            conditions_summary="",
            fetched_at=fetched_at,
        )
