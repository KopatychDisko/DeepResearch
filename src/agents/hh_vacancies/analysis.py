"""Orchestrate hh.ru employer lookup, vacancy fetch, and structured LLM summaries."""

from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from agents.configuration import Configuration
from agents.hh_vacancies.client import HhApiClient, HhApiUserAgentError
from agents.hh_vacancies.web_scraper import HhWebScrapeError
from agents.hh_vacancies.runtime import require_hh_api_user_agent
from agents.hh_vacancies.employer_search import (
    EmployerSearchMatch,
    build_initial_employer_search_queries,
    search_employer_for_identity,
)
from agents.language import (
    hh_analysis_failed_message,
    hh_employer_not_found,
    hh_employer_not_found_with_tried,
    hh_employer_rating_text,
    hh_employer_rating_unavailable,
    hh_found_vacancies_message,
    hh_no_active_vacancies,
    hh_no_conditions_to_summarize,
    response_language_instruction,
)
from agents.models import (
    CompanyIdentity,
    HhEmployerRating,
    HhVacancyAnalysis,
    HhVacancyItem,
    HhVacancyStatus,
    HhVacancySummary,
    ResponseLanguage,
    StructuredHhEmployerSearchReformulation,
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
        search_queries_tried=[],
        matched_search_query=None,
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


def _rule_based_rating_text(rating: HhEmployerRating, language: ResponseLanguage) -> str:
    if rating.available and rating.average_score is not None:
        return hh_employer_rating_text(language=language, average_score=rating.average_score)
    return hh_employer_rating_unavailable(language=language)


def _rule_based_zero_vacancy_summaries(
    rating: HhEmployerRating,
    language: ResponseLanguage,
) -> tuple[str, str]:
    rating_text: str = _rule_based_rating_text(rating=rating, language=language)
    salary_summary: str = hh_no_active_vacancies(language=language)
    conditions_summary: str = f"{rating_text} {hh_no_conditions_to_summarize(language=language)}"
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
    language: ResponseLanguage,
) -> str:
    return (
        f"{response_language_instruction(language=language)}\n"
        f"Summarize hh.ru vacancy data for employer {identity.canonical_name}.\n"
        f"Employer rating available: {rating.available}\n"
        f"Employer trusted on hh.ru: {rating.trusted}\n"
        f"Vacancies JSON (includes archived, key_skills, description_plain, employer_trusted):\n"
        f"{_vacancies_json_prompt(vacancies)}\n"
        "Produce concise salary_summary, conditions_summary, and employer_rating_text fields. "
        "Flag archived vacancies explicitly. When rating is unavailable, state that explicitly "
        "without inventing numeric scores."
    )


def _combine_conditions_summary(
    conditions_summary: str,
    employer_rating_text: str,
) -> str:
    if employer_rating_text in conditions_summary:
        return conditions_summary
    return f"{conditions_summary}\n\n{employer_rating_text}"


def _append_unique_queries(
    queries: list[str],
    seen: set[str],
    candidates: list[str],
) -> None:
    for candidate in candidates:
        cleaned: str = " ".join(candidate.split())
        if cleaned == "":
            continue
        key: str = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        queries.append(cleaned)


def _reformulate_hh_search_queries(
    identity: CompanyIdentity,
    attempted_queries: list[str],
    config: RunnableConfig,
    language: ResponseLanguage,
) -> list[str]:
    attempted_text: str = ", ".join(f"«{query}»" for query in attempted_queries)
    prompt: str = (
        f"{response_language_instruction(language=language)}\n"
        "Suggest up to 3 short employer names as they would appear on hh.ru.\n"
        f"Resolved company: {identity.canonical_name}\n"
        f"User query: {identity.query_name}\n"
        f"Already tried on hh.ru: {attempted_text}\n"
        "Return only realistic hh.ru employer page names in search_queries. "
        "Prefer the main legal brand, not departments or products. "
        "Do not repeat already tried names."
    )
    reformulation: StructuredHhEmployerSearchReformulation = invoke_structured_output(
        config=config,
        model_class=StructuredHhEmployerSearchReformulation,
        prompt=prompt,
    )
    return reformulation.search_queries


def _not_found_message(
    identity: CompanyIdentity,
    search_queries_tried: list[str],
    language: ResponseLanguage,
) -> str:
    if not search_queries_tried:
        return hh_employer_not_found(identity_name=identity.canonical_name, language=language)
    return hh_employer_not_found_with_tried(
        identity_name=identity.canonical_name,
        tried_queries=search_queries_tried,
        language=language,
    )


def _resolve_employer_match(
    client: HhApiClient,
    identity: CompanyIdentity,
    config: RunnableConfig,
    search_query_override: str | None,
    language: ResponseLanguage,
) -> tuple[EmployerSearchMatch | None, list[str]]:
    queries: list[str] = build_initial_employer_search_queries(
        identity=identity,
        search_query_override=search_query_override,
    )
    seen: set[str] = {query.casefold() for query in queries}
    match: EmployerSearchMatch | None = search_employer_for_identity(
        client=client,
        identity=identity,
        search_queries=queries,
    )
    if match is not None:
        return match, queries

    if search_query_override is not None:
        return None, queries

    reformulated: list[str] = _reformulate_hh_search_queries(
        identity=identity,
        attempted_queries=queries,
        config=config,
        language=language,
    )
    retry_queries: list[str] = []
    _append_unique_queries(retry_queries, set(seen), reformulated)
    for query in retry_queries:
        queries.append(query)
        seen.add(query.casefold())
    if retry_queries:
        match = search_employer_for_identity(
            client=client,
            identity=identity,
            search_queries=retry_queries,
        )
    return match, queries


def build_hh_vacancy_analysis(
    identity: CompanyIdentity,
    settings: Configuration,
    client: HhApiClient,
    config: RunnableConfig,
    search_query_override: str | None,
    response_language: ResponseLanguage,
) -> HhVacancyAnalysis:
    """Fetch hh.ru vacancies for identity and build a structured analysis block."""
    fetched_at: str = _utc_now_iso()
    search_query: str = (
        search_query_override.strip()
        if search_query_override is not None
        else identity.canonical_name
    )

    try:
        require_hh_api_user_agent(settings=settings)
        match, search_queries_tried = _resolve_employer_match(
            client=client,
            identity=identity,
            config=config,
            search_query_override=search_query_override,
            language=response_language,
        )
        if match is None:
            return HhVacancyAnalysis(
                status=HhVacancyStatus.NOT_FOUND,
                message=_not_found_message(
                    identity=identity,
                    search_queries_tried=search_queries_tried,
                    language=response_language,
                ),
                search_query=search_query,
                employer=None,
                vacancies=[],
                salary_summary="",
                conditions_summary="",
                fetched_at=fetched_at,
                search_queries_tried=search_queries_tried,
                matched_search_query=None,
            )

        employer_id: str = match.employer_id
        employer_name: str = match.employer_name
        rating: HhEmployerRating = client.fetch_employer_profile(employer_id)
        if rating is None:
            rating = _unavailable_rating()

        vacancies: list[HhVacancyItem] = client.fetch_enriched_active_vacancies(
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
                    language=response_language,
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
                language=response_language,
            )

        return HhVacancyAnalysis(
            status=HhVacancyStatus.FOUND,
            message=hh_found_vacancies_message(
                employer_name=employer_name,
                vacancy_count=len(vacancies),
                language=response_language,
            ),
            search_query=search_query,
            employer=employer,
            vacancies=vacancies,
            salary_summary=salary_summary,
            conditions_summary=conditions_summary,
            fetched_at=fetched_at,
            search_queries_tried=search_queries_tried,
            matched_search_query=match.matched_search_query,
        )
    except (HhApiUserAgentError, HhWebScrapeError) as error:
        return HhVacancyAnalysis(
            status=HhVacancyStatus.ERROR,
            message=str(error),
            search_query=search_query,
            employer=None,
            vacancies=[],
            salary_summary="",
            conditions_summary="",
            fetched_at=fetched_at,
            search_queries_tried=[],
            matched_search_query=None,
        )
    except Exception as error:
        return HhVacancyAnalysis(
            status=HhVacancyStatus.ERROR,
            message=hh_analysis_failed_message(error=error, language=response_language),
            search_query=search_query,
            employer=None,
            vacancies=[],
            salary_summary="",
            conditions_summary="",
            fetched_at=fetched_at,
            search_queries_tried=[],
            matched_search_query=None,
        )
