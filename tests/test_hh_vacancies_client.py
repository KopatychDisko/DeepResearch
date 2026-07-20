"""Unit tests for the read-only hh.ru API client (mocked HTTP only)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from agents.configuration import Configuration
from agents.hh_vacancies.client import HhApiClient, HhApiUserAgentError
from agents.models import HhEmployerRating, HhVacancyItem

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures" / "hh"
HH_API_BASE: str = "https://api.hh.ru"
CANONICAL_NAME: str = "Яндекс"
USER_AGENT: str = "EmployerDD/1.0 (test@example.com)"
EMPTY_VACANCY_SEARCH: dict[str, object] = {
    "items": [],
    "found": 0,
    "pages": 0,
    "page": 0,
    "per_page": 20,
}


def _mock_vacancies_route(vacancy_list: dict[str, object]) -> None:
    def _vacancy_handler(request: httpx.Request) -> httpx.Response:
        if "employer_id=" in str(request.url):
            return httpx.Response(200, json=vacancy_list)
        return httpx.Response(200, json=EMPTY_VACANCY_SEARCH)

    respx.get(f"{HH_API_BASE}/vacancies").mock(side_effect=_vacancy_handler)


def _load_fixture(name: str) -> dict[str, object]:
    fixture_path: Path = FIXTURES_DIR / name
    raw_text: str = fixture_path.read_text(encoding="utf-8")
    parsed: object = json.loads(raw_text)
    if not isinstance(parsed, dict):
        raise ValueError(f"Fixture {name} must be a JSON object")
    return parsed


@pytest.fixture
def settings() -> Configuration:
    return Configuration(hh_api_user_agent=USER_AGENT)


@pytest.fixture
def client(settings: Configuration) -> HhApiClient:
    return HhApiClient(settings)


@respx.mock
def test_search_employer_by_name_finds_employer_and_fetches_profile_and_vacancies(
    client: HhApiClient,
) -> None:
    employer_search: dict[str, object] = _load_fixture("employer_search.json")
    employer_profile: dict[str, object] = _load_fixture("employer_profile.json")
    vacancy_list: dict[str, object] = _load_fixture("vacancy_list.json")
    empty_vacancy_search: dict[str, object] = {"items": [], "found": 0, "pages": 0, "page": 0, "per_page": 20}

    respx.get(f"{HH_API_BASE}/employers").mock(return_value=httpx.Response(200, json=employer_search))
    _mock_vacancies_route(vacancy_list)
    respx.get(f"{HH_API_BASE}/employers/1740").mock(return_value=httpx.Response(200, json=employer_profile))

    match = client.search_employer_by_name(CANONICAL_NAME)
    assert match is not None
    employer_id, employer_name = match
    assert employer_id == "1740"
    assert employer_name == "Яндекс"

    rating: HhEmployerRating | None = client.fetch_employer_profile(employer_id)
    assert rating is not None
    assert rating.available is True
    assert rating.average_score == 4.2
    assert rating.trusted is True

    vacancies: list[HhVacancyItem] = client.fetch_active_vacancies(employer_id, 10)
    assert len(vacancies) == 10
    assert vacancies[0].vacancy_id == "10000001"
    assert vacancies[0].title == "Python-разработчик"


@respx.mock
def test_empty_employer_search_returns_none_without_fabricated_data(
    client: HhApiClient,
) -> None:
    empty_search: dict[str, object] = _load_fixture("employer_search_empty.json")
    respx.get(f"{HH_API_BASE}/employers").mock(return_value=httpx.Response(200, json=empty_search))
    _mock_vacancies_route(EMPTY_VACANCY_SEARCH)

    match = client.search_employer_by_name("Nonexistent Corp XYZ")
    assert match is None


@respx.mock
def test_fetch_active_vacancies_caps_results_at_ten(client: HhApiClient) -> None:
    vacancy_list: dict[str, object] = _load_fixture("vacancy_list.json")
    respx.get(f"{HH_API_BASE}/vacancies").mock(return_value=httpx.Response(200, json=vacancy_list))

    vacancies: list[HhVacancyItem] = client.fetch_active_vacancies("1740", 10)
    assert len(vacancies) == 10
    vacancy_ids: list[str] = [item.vacancy_id for item in vacancies]
    assert "10000011" not in vacancy_ids
    assert "10000012" not in vacancy_ids


@respx.mock
def test_all_requests_send_configured_user_agent_header(client: HhApiClient) -> None:
    employer_search: dict[str, object] = _load_fixture("employer_search.json")
    employer_profile: dict[str, object] = _load_fixture("employer_profile.json")
    vacancy_list: dict[str, object] = _load_fixture("vacancy_list.json")
    vacancy_detail: dict[str, object] = _load_fixture("vacancy_detail.json")

    employer_route = respx.get(f"{HH_API_BASE}/employers").mock(
        return_value=httpx.Response(200, json=employer_search)
    )
    profile_route = respx.get(f"{HH_API_BASE}/employers/1740").mock(
        return_value=httpx.Response(200, json=employer_profile)
    )

    def _vacancy_handler(request: httpx.Request) -> httpx.Response:
        if "employer_id=" in str(request.url):
            return httpx.Response(200, json=vacancy_list)
        return httpx.Response(200, json=EMPTY_VACANCY_SEARCH)

    vacancies_route = respx.get(f"{HH_API_BASE}/vacancies").mock(side_effect=_vacancy_handler)
    respx.get(url__regex=rf"{HH_API_BASE}/vacancies/\d+").mock(
        return_value=httpx.Response(200, json=vacancy_detail)
    )

    match = client.search_employer_by_name(CANONICAL_NAME)
    assert match is not None
    client.fetch_employer_profile(match[0])
    client.fetch_enriched_active_vacancies(match[0], 10)

    for route in (employer_route, profile_route, vacancies_route):
        assert route.called
        for call in route.calls:
            assert call.request.headers.get("User-Agent") == USER_AGENT


@respx.mock
def test_429_response_is_retried_with_backoff_then_succeeds(client: HhApiClient) -> None:
    employer_search: dict[str, object] = _load_fixture("employer_search.json")
    route = respx.get(f"{HH_API_BASE}/employers").mock(
        side_effect=[
            httpx.Response(429, json={"errors": [{"type": "too_many_requests"}]}),
            httpx.Response(429, json={"errors": [{"type": "too_many_requests"}]}),
            httpx.Response(200, json=employer_search),
            httpx.Response(200, json=employer_search),
        ]
    )
    _mock_vacancies_route(EMPTY_VACANCY_SEARCH)

    match = client.search_employer_by_name(CANONICAL_NAME)
    assert match is not None
    assert route.call_count >= 3


@respx.mock
def test_bad_user_agent_raises_clear_error() -> None:
    settings = Configuration(hh_api_user_agent="EmployerDD/1.0 (contact@example.com)")
    client = HhApiClient(settings)
    respx.get(f"{HH_API_BASE}/employers").mock(
        return_value=httpx.Response(
            400,
            json={
                "description": "Bad User-Agent header",
                "errors": [{"value": "blacklisted", "type": "bad_user_agent"}],
            },
        )
    )
    try:
        with pytest.raises(HhApiUserAgentError, match="HH.ru API requires a registered User-Agent"):
            client.collect_employer_candidates("Сбер")
    finally:
        client.close()


@respx.mock
def test_fetch_vacancy_detail_returns_parsed_item(client: HhApiClient) -> None:
    vacancy_detail: dict[str, object] = _load_fixture("vacancy_detail.json")
    respx.get(f"{HH_API_BASE}/vacancies/10000001").mock(
        return_value=httpx.Response(200, json=vacancy_detail)
    )

    item: HhVacancyItem | None = client.fetch_vacancy_detail("10000001")
    assert item is not None
    assert item.vacancy_id == "10000001"
    assert item.schedule == "Удаленная работа"
    assert item.archived is False
    assert item.key_skills == ["Python", "FastAPI"]
    assert item.description_plain == "Разработка backend-сервисов на Python."
    assert item.employer_trusted is True
