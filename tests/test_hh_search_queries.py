"""Tests for hh.ru employer search query extraction."""

from __future__ import annotations

from agents.hh_vacancies.client import employer_match_score
from agents.hh_vacancies.search_queries import extract_employer_search_queries
from agents.models import CompanyIdentity


def _identity(canonical_name: str, query_name: str) -> CompanyIdentity:
    return CompanyIdentity(
        query_name=query_name,
        canonical_name=canonical_name,
        normalized_name=canonical_name.casefold(),
        company_url=None,
        profile_summary=None,
        user_description=None,
    )


def test_extract_queries_from_parenthetical_sber_name() -> None:
    identity = _identity("Сбер (Sber / Сбербанк)", "Сбер")
    queries = extract_employer_search_queries(
        identity=identity,
        search_query_override=None,
    )

    assert "Сбер (Sber / Сбербанк)" in queries
    assert "Сбер" in queries
    assert "Сбербанк" in queries
    assert "Sber" in queries


def test_sber_name_matches_sberbank_employer() -> None:
    score = employer_match_score("Сбер (Sber / Сбербанк)", "Сбер")
    assert score >= 0.9

    score_sberbank = employer_match_score("Сбер (Sber / Сбербанк)", "Сбербанк")
    assert score_sberbank >= 0.9


def test_override_query_is_used_exclusively() -> None:
    identity = _identity("Сбер (Sber / Сбербанк)", "Сбер")
    queries = extract_employer_search_queries(
        identity=identity,
        search_query_override="ПАО Сбербанк",
    )

    assert queries[0] == "ПАО Сбербанк"
    assert "Сбер (Sber / Сбербанк)" not in queries
