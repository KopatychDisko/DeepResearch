from __future__ import annotations

from pydantic import AnyHttpUrl

from agents.identity.resolution import (
    _pick_auto_confirmed_candidate,
    normalize_host,
)
from agents.models import CompanyCandidate, Confidence


def _candidate(
    name: str,
    description: str,
    website_url: str | None,
    confidence: Confidence,
) -> CompanyCandidate:
    return CompanyCandidate(
        candidate_id="test-id",
        name=name,
        description=description,
        website_url=AnyHttpUrl(website_url) if website_url is not None else None,
        confidence=confidence,
    )


def test_identity_search_query_includes_description() -> None:
    from pydantic import AnyHttpUrl

    from agents.identity.resolution import _build_identity_search_query

    query: str = _build_identity_search_query(
        company_name="Ромашка",
        company_url=None,
        company_description="сеть цветочных магазинов Москва",
    )
    assert "сеть цветочных магазинов" in query
    assert "Ромашка" in query


def test_normalize_host_strips_www() -> None:
    assert normalize_host("https://www.yandex.ru/about") == "yandex.ru"


def test_auto_confirm_when_single_url_match() -> None:
    candidates: list[CompanyCandidate] = [
        _candidate("Яндекс", "IT-компания", "https://yandex.ru", Confidence.HIGH),
        _candidate("Яндекс Такси", "Такси", "https://taxi.yandex.ru", Confidence.MEDIUM),
    ]
    selected = _pick_auto_confirmed_candidate(
        candidates=candidates,
        requested_company_url=AnyHttpUrl("https://yandex.ru/company"),
    )
    assert selected is not None
    assert selected.name == "Яндекс"


def test_auto_confirm_single_high_confidence_candidate() -> None:
    candidates: list[CompanyCandidate] = [
        _candidate("Acme Corp", "Manufacturing", "https://acme.example", Confidence.HIGH),
    ]
    selected = _pick_auto_confirmed_candidate(
        candidates=candidates,
        requested_company_url=None,
    )
    assert selected is not None
    assert selected.name == "Acme Corp"


def test_no_auto_confirm_for_multiple_strong_candidates() -> None:
    candidates: list[CompanyCandidate] = [
        _candidate("Ромашка ООО", "Цветы", "https://romashka-a.ru", Confidence.HIGH),
        _candidate("Ромашка Агро", "Агро", "https://romashka-b.ru", Confidence.HIGH),
    ]
    selected = _pick_auto_confirmed_candidate(
        candidates=candidates,
        requested_company_url=None,
    )
    assert selected is None
