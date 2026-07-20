"""Read-only hh.ru website scraper when api.hh.ru returns anti-bot 403."""

from __future__ import annotations

import html
import json
import re
import time
from typing import cast
from urllib.parse import urlencode

import httpx

from agents.hh_vacancies.html_utils import strip_html
from agents.models import HhEmployerRating, HhSalaryRange, HhVacancyItem

HH_WEB_BASE_URL: str = "https://hh.ru"
HH_WEB_BROWSER_USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HH_AREA_RUSSIA: int = 113
INITIAL_STATE_PATTERN: re.Pattern[str] = re.compile(
    r'id="HH-Lux-InitialState">([^<]+)</template>',
)
VACANCY_DETAIL_DELAY_SECONDS: float = 0.15


class HhWebScrapeError(RuntimeError):
    """Raised when hh.ru website scraping fails."""


def extract_initial_state(page_html: str) -> dict[str, object]:
    """Parse embedded HH-Lux-InitialState JSON from an hh.ru HTML page."""
    match: re.Match[str] | None = INITIAL_STATE_PATTERN.search(page_html)
    if match is None:
        raise HhWebScrapeError("hh.ru page is missing HH-Lux-InitialState payload")
    decoded_json: str = html.unescape(match.group(1))
    parsed_payload: object = json.loads(decoded_json)
    if not isinstance(parsed_payload, dict):
        raise HhWebScrapeError("hh.ru initial state payload is not a JSON object")
    return cast(dict[str, object], parsed_payload)


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []


def _as_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized: str = value.strip().replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return None
    return None


def _as_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def parse_web_compensation(compensation_payload: object) -> HhSalaryRange | None:
    """Map hh.ru website compensation JSON to HhSalaryRange."""
    if not isinstance(compensation_payload, dict):
        return None
    return HhSalaryRange(
        from_amount=_as_int(compensation_payload.get("from")),
        to_amount=_as_int(compensation_payload.get("to")),
        currency=_as_str(compensation_payload.get("currencyCode")),
        gross=_as_bool(compensation_payload.get("gross")),
    )


def _parse_web_key_skills(key_skills_payload: object) -> list[str]:
    if not isinstance(key_skills_payload, dict):
        return []
    raw_skills: object = key_skills_payload.get("keySkill")
    if not isinstance(raw_skills, list):
        return []
    skills: list[str] = []
    for skill in raw_skills:
        if isinstance(skill, str) and skill.strip() != "":
            skills.append(skill.strip())
    return skills


def _parse_web_working_conditions(item: dict[str, object]) -> list[str]:
    labels: list[str] = []
    for key in ("workScheduleByDays", "workingHours", "workFormats"):
        value: object = item.get(key)
        if isinstance(value, list):
            for entry in value:
                label: str | None = _as_str(entry)
                if label is not None:
                    labels.append(label)
        else:
            label = _as_str(value)
            if label is not None:
                labels.append(label)
    return labels


def _company_trusted_flag(company_payload: object) -> bool | None:
    company: dict[str, object] = _as_dict(company_payload)
    return _as_bool(company.get("@trusted"))


def parse_web_vacancy_search_item(item: dict[str, object]) -> HhVacancyItem:
    """Map a vacancy row from hh.ru search results to HhVacancyItem."""
    vacancy_id: str | None = _as_str(item.get("vacancyId"))
    title: str | None = _as_str(item.get("name"))
    if vacancy_id is None or title is None:
        raise ValueError("Vacancy search item is missing vacancyId or name")

    area_payload: dict[str, object] = _as_dict(item.get("area"))
    company_payload: dict[str, object] = _as_dict(item.get("company"))
    employment_payload: dict[str, object] = _as_dict(item.get("employment"))
    employment_form: str | None = _as_str(item.get("employmentForm"))
    if employment_form is None:
        employment_form = _as_str(employment_payload.get("name"))

    return HhVacancyItem(
        vacancy_id=vacancy_id,
        title=title,
        url=f"https://hh.ru/vacancy/{vacancy_id}",
        area_name=_as_str(area_payload.get("name")),
        salary=parse_web_compensation(item.get("compensation")),
        employment_type=employment_form,
        schedule=_as_str(item.get("workScheduleByDays")),
        experience=_as_str(item.get("workExperience")),
        working_conditions=_parse_web_working_conditions(item),
        published_at=_as_str(item.get("publicationTime")),
        archived=None,
        key_skills=[],
        description_plain=None,
        employer_trusted=_company_trusted_flag(company_payload),
    )


def parse_web_vacancy_detail_view(view: dict[str, object]) -> HhVacancyItem:
    """Map hh.ru vacancyView JSON to HhVacancyItem."""
    vacancy_id: str | None = _as_str(view.get("vacancyId"))
    title: str | None = _as_str(view.get("name"))
    if vacancy_id is None or title is None:
        raise ValueError("Vacancy detail view is missing vacancyId or name")

    area_payload: dict[str, object] = _as_dict(view.get("area"))
    company_payload: dict[str, object] = _as_dict(view.get("company"))
    description_value: str | None = _as_str(view.get("description"))
    description_plain: str | None = None
    if description_value is not None and description_value.strip() != "":
        description_plain = strip_html(description_value)

    status_value: str | None = _as_str(view.get("status"))
    archived: bool | None = None
    if status_value is not None:
        archived = status_value.casefold() in {"archived", "closed"}

    return HhVacancyItem(
        vacancy_id=vacancy_id,
        title=title,
        url=f"https://hh.ru/vacancy/{vacancy_id}",
        area_name=_as_str(area_payload.get("name")),
        salary=parse_web_compensation(view.get("compensation")),
        employment_type=_as_str(view.get("employmentForm")),
        schedule=_as_str(view.get("workScheduleByDays")),
        experience=_as_str(view.get("workExperience")),
        working_conditions=_parse_web_working_conditions(view),
        published_at=_as_str(view.get("publicationDate")),
        archived=archived,
        key_skills=_parse_web_key_skills(view.get("keySkills")),
        description_plain=description_plain,
        employer_trusted=_company_trusted_flag(company_payload),
    )


def parse_web_employer_rating(
    employer_info: dict[str, object],
    employer_id: str,
    reviews_payload: dict[str, object] | None,
) -> HhEmployerRating:
    """Map hh.ru employer page fields to HhEmployerRating."""
    average_score: float | None = None
    reviews_count: int | None = None
    available: bool = False
    if reviews_payload is not None:
        average_score = _as_float(reviews_payload.get("totalRating"))
        reviews_count = _as_int(reviews_payload.get("reviewsCount"))
        if average_score is not None:
            available = True

    return HhEmployerRating(
        available=available,
        average_score=average_score,
        reviews_count=reviews_count,
        recommendation_percent=None,
        trusted=_as_bool(employer_info.get("isTrusted")),
        accredited_it_employer=_as_bool(employer_info.get("accreditedITEmployer")),
        source_url=f"https://hh.ru/employer/{employer_id}",
    )


def flatten_employers_list(state: dict[str, object]) -> list[dict[str, object]]:
    """Flatten grouped employersList payload into API-shaped employer rows."""
    employers_list: dict[str, object] = _as_dict(state.get("employersList"))
    grouped_employers: object = employers_list.get("employers")
    if not isinstance(grouped_employers, dict):
        return []

    flattened: list[dict[str, object]] = []
    for group_items in grouped_employers.values():
        for item in _as_list(group_items):
            if not isinstance(item, dict):
                continue
            employer_id: str | None = _as_str(item.get("id"))
            employer_name: str | None = _as_str(item.get("name"))
            if employer_id is None or employer_name is None:
                continue
            flattened.append(
                {
                    "id": employer_id,
                    "name": employer_name,
                    "open_vacancies": item.get("vacanciesOpen"),
                }
            )
    return flattened


def extract_employers_from_vacancy_search(state: dict[str, object]) -> list[dict[str, object]]:
    """Extract unique employers from vacancy search results."""
    search_result: dict[str, object] = _as_dict(state.get("vacancySearchResult"))
    vacancies: list[object] = _as_list(search_result.get("vacancies"))
    merged: dict[str, dict[str, object]] = {}
    for vacancy in vacancies:
        if not isinstance(vacancy, dict):
            continue
        company: dict[str, object] = _as_dict(vacancy.get("company"))
        employer_id: str | None = _as_str(company.get("id"))
        employer_name: str | None = _as_str(company.get("name"))
        if employer_id is None or employer_name is None:
            continue
        merged[employer_id] = {
            "id": employer_id,
            "name": employer_name,
            "open_vacancies": None,
            "trusted": company.get("@trusted"),
        }
    return list(merged.values())


def _merge_employer_items(
    merged: dict[str, dict[str, object]],
    items: list[dict[str, object]],
) -> None:
    for item in items:
        employer_id: str | None = _as_str(item.get("id"))
        if employer_id is None:
            continue
        merged[employer_id] = item


def _extract_company_reviews(company_payload: object) -> dict[str, object] | None:
    company: dict[str, object] = _as_dict(company_payload)
    reviews: dict[str, object] = _as_dict(company.get("employerReviews"))
    if not reviews:
        return None
    return reviews


class HhWebScraper:
    """Fetch public hh.ru vacancy data from website HTML when API access is blocked."""

    def __init__(self) -> None:
        self._client: httpx.Client = httpx.Client(
            headers={
                "User-Agent": HH_WEB_BROWSER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ru-RU,ru;q=0.9",
            },
            follow_redirects=True,
            timeout=httpx.Timeout(30.0),
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def _fetch_state(self, path: str, params: dict[str, str | int]) -> dict[str, object]:
        query: str = urlencode(params)
        request_url: str = f"{HH_WEB_BASE_URL}{path}?{query}"
        response: httpx.Response = self._client.get(request_url)
        if response.status_code >= 400:
            raise HhWebScrapeError(
                f"hh.ru website request failed: url={request_url} status={response.status_code}"
            )
        return extract_initial_state(response.text)

    def collect_employer_candidates(self, search_text: str) -> list[dict[str, object]]:
        """Search employers via hh.ru employers list and vacancy search pages."""
        merged: dict[str, dict[str, object]] = {}

        list_state: dict[str, object] = self._fetch_state(
            "/employers_list",
            {"query": search_text},
        )
        _merge_employer_items(merged=merged, items=flatten_employers_list(list_state))

        for search_field in ("company_name", ""):
            params: dict[str, str | int] = {
                "text": search_text,
                "area": HH_AREA_RUSSIA,
            }
            if search_field != "":
                params["search_field"] = search_field
            search_state: dict[str, object] = self._fetch_state("/search/vacancy", params)
            _merge_employer_items(
                merged=merged,
                items=extract_employers_from_vacancy_search(search_state),
            )

        return list(merged.values())

    def fetch_employer_profile(self, employer_id: str) -> HhEmployerRating | None:
        """Fetch employer trust and rating signals from the employer page."""
        state: dict[str, object] = self._fetch_state(f"/employer/{employer_id}", {})
        employer_info: dict[str, object] = _as_dict(state.get("employerInfo"))
        if not employer_info:
            return None

        reviews_payload: dict[str, object] | None = None
        search_state: dict[str, object] = self._fetch_state(
            "/search/vacancy",
            {"employer_id": employer_id, "area": HH_AREA_RUSSIA, "per_page": 1},
        )
        search_result: dict[str, object] = _as_dict(search_state.get("vacancySearchResult"))
        vacancies: list[object] = _as_list(search_result.get("vacancies"))
        if vacancies and isinstance(vacancies[0], dict):
            reviews_payload = _extract_company_reviews(vacancies[0].get("company"))

        return parse_web_employer_rating(
            employer_info=employer_info,
            employer_id=employer_id,
            reviews_payload=reviews_payload,
        )

    def fetch_active_vacancies(self, employer_id: str, max_count: int) -> list[HhVacancyItem]:
        """Fetch active vacancies for an employer from hh.ru search results."""
        if max_count <= 0:
            return []

        state: dict[str, object] = self._fetch_state(
            "/search/vacancy",
            {"employer_id": employer_id, "area": HH_AREA_RUSSIA},
        )
        search_result: dict[str, object] = _as_dict(state.get("vacancySearchResult"))
        vacancies: list[HhVacancyItem] = []
        for item in _as_list(search_result.get("vacancies")):
            if not isinstance(item, dict):
                continue
            vacancies.append(parse_web_vacancy_search_item(item))
            if len(vacancies) >= max_count:
                break
        return vacancies

    def fetch_vacancy_detail(self, vacancy_id: str) -> HhVacancyItem | None:
        """Fetch vacancy detail fields from the hh.ru vacancy page."""
        state: dict[str, object] = self._fetch_state(f"/vacancy/{vacancy_id}", {})
        vacancy_view: dict[str, object] = _as_dict(state.get("vacancyView"))
        if not vacancy_view:
            return None
        return parse_web_vacancy_detail_view(vacancy_view)

    def fetch_enriched_active_vacancies(
        self,
        employer_id: str,
        max_count: int,
    ) -> list[HhVacancyItem]:
        """Fetch employer vacancies and enrich each row from vacancy detail pages."""
        listed_vacancies: list[HhVacancyItem] = self.fetch_active_vacancies(
            employer_id,
            max_count,
        )
        enriched_vacancies: list[HhVacancyItem] = []
        for index, vacancy in enumerate(listed_vacancies):
            if index > 0:
                time.sleep(VACANCY_DETAIL_DELAY_SECONDS)
            detailed_vacancy: HhVacancyItem | None = self.fetch_vacancy_detail(
                vacancy.vacancy_id,
            )
            if detailed_vacancy is None:
                enriched_vacancies.append(vacancy)
                continue
            enriched_vacancies.append(detailed_vacancy)
        return enriched_vacancies
