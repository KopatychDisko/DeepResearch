"""Employer search orchestration across multiple hh.ru query variants."""

from __future__ import annotations

from dataclasses import dataclass

from agents.hh_vacancies.client import HhApiClient, employer_match_score
from agents.models import CompanyIdentity
from agents.hh_vacancies.search_queries import extract_employer_search_queries

MIN_EMPLOYER_MATCH_SCORE: float = 0.15


@dataclass(frozen=True)
class EmployerSearchMatch:
    """Best employer match returned from hh.ru search."""

    employer_id: str
    employer_name: str
    matched_search_query: str
    score: float


def _score_employer_match(
    identity: CompanyIdentity,
    search_queries: list[str],
    active_query: str,
    employer_name: str,
) -> float:
    candidate_names: list[str] = [
        identity.canonical_name,
        identity.query_name,
        active_query,
    ]
    candidate_names.extend(search_queries)
    seen: set[str] = set()
    best_score: float = 0.0
    for candidate_name in candidate_names:
        normalized_key: str = candidate_name.casefold()
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        score: float = employer_match_score(candidate_name, employer_name)
        if score > best_score:
            best_score = score
    return best_score


def search_employer_for_identity(
    client: HhApiClient,
    identity: CompanyIdentity,
    search_queries: list[str],
) -> EmployerSearchMatch | None:
    """Try each query variant and return the highest-scoring employer match."""
    best_match: EmployerSearchMatch | None = None
    seen_employer_ids: set[str] = set()

    for query in search_queries:
        items: list[dict[str, object]] = client.collect_employer_candidates(query)
        for item in items:
            employer_id_value = item.get("id")
            employer_name_value = item.get("name")
            if not isinstance(employer_id_value, (str, int)) or not isinstance(
                employer_name_value,
                str,
            ):
                continue
            employer_id: str = str(employer_id_value)
            if employer_id in seen_employer_ids:
                continue
            seen_employer_ids.add(employer_id)

            score: float = _score_employer_match(
                identity=identity,
                search_queries=search_queries,
                active_query=query,
                employer_name=employer_name_value,
            )
            if score < MIN_EMPLOYER_MATCH_SCORE:
                continue
            if best_match is None or score > best_match.score:
                best_match = EmployerSearchMatch(
                    employer_id=employer_id,
                    employer_name=employer_name_value,
                    matched_search_query=query,
                    score=score,
                )

    return best_match


def build_initial_employer_search_queries(
    identity: CompanyIdentity,
    search_query_override: str | None,
) -> list[str]:
    """Build the first-pass employer search query list for an identity."""
    return extract_employer_search_queries(
        identity=identity,
        search_query_override=search_query_override,
    )
