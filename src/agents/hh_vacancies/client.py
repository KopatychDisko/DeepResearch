"""Read-only client for the public api.hh.ru REST API."""

from __future__ import annotations

import re
import time
from typing import cast

import httpx

from agents.configuration import Configuration
from agents.models import HhEmployerRating, HhSalaryRange, HhVacancyItem

HH_API_BASE_URL: str = "https://api.hh.ru"
MAX_RETRY_ATTEMPTS: int = 3
RETRY_BACKOFF_SECONDS: tuple[float, ...] = (0.1, 0.2)

LEGAL_SUFFIX_PATTERN: re.Pattern[str] = re.compile(
    r"\b(ооо|ао|пао|зао|оао|llc|ltd|inc)\b",
    re.IGNORECASE,
)


def normalize_employer_name(name: str) -> str:
    """Normalize employer names for exact and fuzzy matching."""
    lowered_name: str = name.casefold().strip()
    without_suffix: str = LEGAL_SUFFIX_PATTERN.sub("", lowered_name)
    return " ".join(without_suffix.split())


def token_overlap_score(left_name: str, right_name: str) -> float:
    """Return Jaccard similarity between normalized employer name tokens."""
    left_tokens: set[str] = set(normalize_employer_name(left_name).split())
    right_tokens: set[str] = set(normalize_employer_name(right_name).split())
    if not left_tokens or not right_tokens:
        return 0.0
    intersection_size: int = len(left_tokens & right_tokens)
    union_size: int = len(left_tokens | right_tokens)
    return intersection_size / union_size


def parse_salary_range(salary_payload: dict[str, object] | None) -> HhSalaryRange | None:
    """Map hh.ru salary JSON to HhSalaryRange."""
    if salary_payload is None:
        return None
    from_value = salary_payload.get("from")
    to_value = salary_payload.get("to")
    currency_value = salary_payload.get("currency")
    gross_value = salary_payload.get("gross")
    return HhSalaryRange(
        from_amount=from_value if isinstance(from_value, int) else None,
        to_amount=to_value if isinstance(to_value, int) else None,
        currency=currency_value if isinstance(currency_value, str) else None,
        gross=gross_value if isinstance(gross_value, bool) else None,
    )


def _named_labels(payload_items: object) -> list[str]:
    if not isinstance(payload_items, list):
        return []
    labels: list[str] = []
    for item in payload_items:
        if not isinstance(item, dict):
            continue
        name_value = item.get("name")
        if isinstance(name_value, str) and name_value:
            labels.append(name_value)
    return labels


def parse_vacancy_item(vacancy_payload: dict[str, object]) -> HhVacancyItem:
    """Map hh.ru vacancy JSON to HhVacancyItem."""
    vacancy_id_value = vacancy_payload.get("id")
    if not isinstance(vacancy_id_value, (str, int)):
        raise ValueError("Vacancy payload is missing id")

    title_value = vacancy_payload.get("name")
    if not isinstance(title_value, str):
        raise ValueError("Vacancy payload is missing name")

    url_value = vacancy_payload.get("alternate_url")
    if not isinstance(url_value, str):
        raise ValueError("Vacancy payload is missing alternate_url")

    area_payload = vacancy_payload.get("area")
    area_name: str | None = None
    if isinstance(area_payload, dict):
        area_name_value = area_payload.get("name")
        if isinstance(area_name_value, str):
            area_name = area_name_value

    employment_payload = vacancy_payload.get("employment")
    employment_type: str | None = None
    if isinstance(employment_payload, dict):
        employment_name = employment_payload.get("name")
        if isinstance(employment_name, str):
            employment_type = employment_name

    schedule_payload = vacancy_payload.get("schedule")
    schedule: str | None = None
    if isinstance(schedule_payload, dict):
        schedule_name = schedule_payload.get("name")
        if isinstance(schedule_name, str):
            schedule = schedule_name

    experience_payload = vacancy_payload.get("experience")
    experience: str | None = None
    if isinstance(experience_payload, dict):
        experience_name = experience_payload.get("name")
        if isinstance(experience_name, str):
            experience = experience_name

    salary_payload = vacancy_payload.get("salary")
    salary: HhSalaryRange | None = None
    if isinstance(salary_payload, dict):
        salary = parse_salary_range(salary_payload)

    working_conditions: list[str] = []
    working_conditions.extend(_named_labels(vacancy_payload.get("working_days")))
    working_conditions.extend(_named_labels(vacancy_payload.get("working_time_modes")))

    published_at_value = vacancy_payload.get("published_at")
    published_at: str | None = published_at_value if isinstance(published_at_value, str) else None

    return HhVacancyItem(
        vacancy_id=str(vacancy_id_value),
        title=title_value,
        url=url_value,
        area_name=area_name,
        salary=salary,
        employment_type=employment_type,
        schedule=schedule,
        experience=experience,
        working_conditions=working_conditions,
        published_at=published_at,
    )


def parse_employer_rating(
    profile_payload: dict[str, object],
) -> HhEmployerRating:
    """Map hh.ru employer profile JSON to HhEmployerRating."""
    alternate_url_value = profile_payload.get("alternate_url")
    source_url: str | None = alternate_url_value if isinstance(alternate_url_value, str) else None

    trusted_value = profile_payload.get("trusted")
    accredited_value = profile_payload.get("accredited_it_employer")

    rating_payload = profile_payload.get("employer_rating")
    average_score: float | None = None
    reviews_count: int | None = None
    recommendation_percent: float | None = None
    available: bool = False
    if isinstance(rating_payload, dict):
        total_rating = rating_payload.get("total_rating")
        if isinstance(total_rating, (int, float)):
            average_score = float(total_rating)
            available = True
        reviews_count_value = rating_payload.get("reviews_count")
        if isinstance(reviews_count_value, int):
            reviews_count = reviews_count_value
        recommendation_value = rating_payload.get("recommendation_percent")
        if isinstance(recommendation_value, (int, float)):
            recommendation_percent = float(recommendation_value)

    return HhEmployerRating(
        available=available,
        average_score=average_score,
        reviews_count=reviews_count,
        recommendation_percent=recommendation_percent,
        trusted=trusted_value if isinstance(trusted_value, bool) else None,
        accredited_it_employer=accredited_value if isinstance(accredited_value, bool) else None,
        source_url=source_url,
    )


def _select_employer_match(
    canonical_name: str,
    items: list[dict[str, object]],
) -> tuple[str, str] | None:
    if not items:
        return None

    normalized_query: str = normalize_employer_name(canonical_name)
    exact_matches: list[tuple[str, str]] = []
    for item in items:
        employer_id_value = item.get("id")
        employer_name_value = item.get("name")
        if not isinstance(employer_id_value, (str, int)) or not isinstance(employer_name_value, str):
            continue
        if normalize_employer_name(employer_name_value) == normalized_query:
            exact_matches.append((str(employer_id_value), employer_name_value))

    if exact_matches:
        return exact_matches[0]

    scored_matches: list[tuple[float, str, str]] = []
    for item in items:
        employer_id_value = item.get("id")
        employer_name_value = item.get("name")
        if not isinstance(employer_id_value, (str, int)) or not isinstance(employer_name_value, str):
            continue
        score: float = token_overlap_score(canonical_name, employer_name_value)
        scored_matches.append((score, str(employer_id_value), employer_name_value))

    if not scored_matches:
        return None

    scored_matches.sort(key=lambda entry: entry[0], reverse=True)
    best_score, best_id, best_name = scored_matches[0]
    if best_score <= 0.0:
        return None
    return best_id, best_name


class HhApiClient:
    """Connector for read-only hh.ru API requests with retries and parsing helpers."""

    def __init__(self, settings: Configuration) -> None:
        self._settings: Configuration = settings
        self._client: httpx.Client = httpx.Client(
            base_url=HH_API_BASE_URL,
            headers={
                "User-Agent": settings.hh_api_user_agent,
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0),
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def _get_json(
        self,
        path: str,
        params: dict[str, str | int | bool],
    ) -> dict[str, object]:
        last_error: Exception | None = None
        request_url: str = f"{HH_API_BASE_URL}{path}"

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                response: httpx.Response = self._client.get(path, params=params)
                if response.status_code == 429 or response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"HH API returned retryable status {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                parsed_payload: object = response.json()
                if not isinstance(parsed_payload, dict):
                    raise ValueError(f"HH API returned non-object JSON for {request_url}")
                return cast(dict[str, object], parsed_payload)
            except (httpx.HTTPStatusError, httpx.TransportError) as error:
                last_error = error
                status_code: int | None = None
                if isinstance(error, httpx.HTTPStatusError) and error.response is not None:
                    status_code = error.response.status_code
                if attempt < MAX_RETRY_ATTEMPTS:
                    backoff_index: int = attempt - 1
                    if backoff_index < len(RETRY_BACKOFF_SECONDS):
                        time.sleep(RETRY_BACKOFF_SECONDS[backoff_index])
                    print(
                        "Warning: HH API request retry",
                        {
                            "attempt": attempt,
                            "max_attempts": MAX_RETRY_ATTEMPTS,
                            "url": request_url,
                            "status_code": status_code,
                            "error_type": type(error).__name__,
                        },
                    )
                    continue
                break

        if last_error is None:
            raise RuntimeError(f"HH API request failed with unknown error for {request_url}")
        if isinstance(last_error, httpx.HTTPStatusError) and last_error.response is not None:
            raise RuntimeError(
                f"HH API request failed after {MAX_RETRY_ATTEMPTS} attempts: "
                f"url={request_url} status={last_error.response.status_code}"
            ) from last_error
        raise RuntimeError(
            f"HH API request failed after {MAX_RETRY_ATTEMPTS} attempts: url={request_url}"
        ) from last_error

    def search_employer_by_name(self, canonical_name: str) -> tuple[str, str] | None:
        """Search employers by canonical name and return the best match id and name."""
        search_params: dict[str, str | int | bool] = {
            "text": canonical_name,
            "only_with_vacancies": True,
            "per_page": 20,
            "page": 0,
            "host": "hh.ru",
        }
        payload: dict[str, object] = self._get_json("/employers", search_params)
        items_value = payload.get("items")
        if not isinstance(items_value, list):
            return None

        typed_items: list[dict[str, object]] = []
        for item in items_value:
            if isinstance(item, dict):
                typed_items.append(item)
        return _select_employer_match(canonical_name, typed_items)

    def fetch_employer_profile(self, employer_id: str) -> HhEmployerRating | None:
        """Fetch employer profile and parse rating signals when present."""
        profile_params: dict[str, str | int | bool] = {"host": "hh.ru"}
        payload: dict[str, object] = self._get_json(f"/employers/{employer_id}", profile_params)
        return parse_employer_rating(payload)

    def fetch_active_vacancies(self, employer_id: str, max_count: int) -> list[HhVacancyItem]:
        """Fetch active vacancies for an employer, capped at max_count."""
        if max_count <= 0:
            return []

        vacancy_params: dict[str, str | int | bool] = {
            "employer_id": employer_id,
            "per_page": max_count,
            "page": 0,
            "order_by": "publication_time",
            "host": "hh.ru",
        }
        payload: dict[str, object] = self._get_json("/vacancies", vacancy_params)
        items_value = payload.get("items")
        if not isinstance(items_value, list):
            return []

        vacancies: list[HhVacancyItem] = []
        for item in items_value:
            if not isinstance(item, dict):
                continue
            vacancies.append(parse_vacancy_item(item))
            if len(vacancies) >= max_count:
                break
        return vacancies

    def fetch_vacancy_detail(self, vacancy_id: str) -> HhVacancyItem | None:
        """Fetch a single vacancy detail payload when enrichment is required."""
        detail_params: dict[str, str | int | bool] = {"host": "hh.ru"}
        payload: dict[str, object] = self._get_json(f"/vacancies/{vacancy_id}", detail_params)
        return parse_vacancy_item(payload)
