"""Read-only client for the public api.hh.ru REST API."""

from __future__ import annotations

import time
from typing import cast

import httpx

from agents.configuration import Configuration
from agents.hh_vacancies.parsing import (
    employer_match_score,
    merge_employer_items,
    normalize_employer_name,
    parse_employer_rating,
    parse_vacancy_item,
    select_employer_match,
    token_overlap_score,
)
from agents.hh_vacancies.runtime import HH_API_SETUP_MESSAGE
from agents.hh_vacancies.web_scraper import HhWebScraper
from agents.models import HhEmployerRating, HhVacancyItem

HH_API_BASE_URL: str = "https://api.hh.ru"
HH_AREA_RUSSIA: int = 113
MAX_RETRY_ATTEMPTS: int = 3
RETRY_BACKOFF_SECONDS: tuple[float, ...] = (0.1, 0.2)
VACANCY_DETAIL_DELAY_SECONDS: float = 0.15


class HhApiUserAgentError(RuntimeError):
    """Raised when hh.ru rejects the configured User-Agent header."""


class HhApiAuthError(RuntimeError):
    """Raised when hh.ru rejects the request due to authorization or access rules."""


class HhApiBlockedError(RuntimeError):
    """Raised when api.hh.ru blocks programmatic access with anti-bot 403."""


class HhApiClient:
    """Connector for read-only hh.ru API requests with retries and parsing helpers."""

    def __init__(self, settings: Configuration) -> None:
        self._settings: Configuration = settings
        self._use_web: bool = False
        self._web_scraper: HhWebScraper | None = None
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
        if self._web_scraper is not None:
            self._web_scraper.close()

    def _web(self) -> HhWebScraper:
        if self._web_scraper is None:
            self._web_scraper = HhWebScraper()
        return self._web_scraper

    def _activate_web_fallback(self) -> None:
        self._use_web = True

    def _call_with_web_fallback(
        self,
        api_call: object,
        web_call: object,
    ) -> object:
        if self._use_web:
            return web_call()
        try:
            return api_call()
        except HhApiBlockedError:
            self._activate_web_fallback()
            return web_call()

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
                if response.status_code in (400, 403):
                    self._raise_auth_error(response=response, request_url=request_url)
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

    def _raise_auth_error(self, response: httpx.Response, request_url: str) -> None:
        body_text: str = response.text
        if response.status_code == 400 and "bad_user_agent" in body_text:
            raise HhApiUserAgentError(HH_API_SETUP_MESSAGE)
        if response.status_code == 403:
            if '"type":"forbidden"' in body_text or '"type": "forbidden"' in body_text:
                raise HhApiBlockedError(
                    f"HH API blocked programmatic access (403 forbidden) for {request_url}."
                )
            raise HhApiAuthError(
                f"HH API access denied (403) for {request_url}. "
                f"{HH_API_SETUP_MESSAGE}"
            )
        response.raise_for_status()

    def _fetch_employers_index(
        self,
        search_text: str,
        only_with_vacancies: bool,
    ) -> list[dict[str, object]]:
        search_params: dict[str, str | int | bool] = {
            "text": search_text,
            "only_with_vacancies": only_with_vacancies,
            "per_page": 20,
            "page": 0,
            "host": "hh.ru",
        }
        payload: dict[str, object] = self._get_json("/employers", search_params)
        items_value = payload.get("items")
        if not isinstance(items_value, list):
            return []

        typed_items: list[dict[str, object]] = []
        for item in items_value:
            if isinstance(item, dict):
                typed_items.append(item)
        return typed_items

    def _fetch_employers_via_vacancies(self, search_text: str) -> list[dict[str, object]]:
        employers: list[dict[str, object]] = []
        seen_ids: set[str] = set()
        search_modes: list[str | None] = ["company_name", None]
        for search_field in search_modes:
            vacancy_params: dict[str, str | int | bool] = {
                "text": search_text,
                "area": HH_AREA_RUSSIA,
                "per_page": 20,
                "page": 0,
                "host": "hh.ru",
                "order_by": "publication_time",
            }
            if search_field is not None:
                vacancy_params["search_field"] = search_field
            payload: dict[str, object] = self._get_json("/vacancies", vacancy_params)
            items_value = payload.get("items")
            if not isinstance(items_value, list):
                continue

            for item in items_value:
                if not isinstance(item, dict):
                    continue
                employer_payload = item.get("employer")
                if not isinstance(employer_payload, dict):
                    continue
                employer_id_value = employer_payload.get("id")
                employer_name_value = employer_payload.get("name")
                if not isinstance(employer_id_value, (str, int)) or not isinstance(
                    employer_name_value,
                    str,
                ):
                    continue
                employer_id: str = str(employer_id_value)
                if employer_id in seen_ids:
                    continue
                seen_ids.add(employer_id)
                employers.append(
                    {
                        "id": employer_id,
                        "name": employer_name_value,
                        "open_vacancies": employer_payload.get("open_vacancies"),
                        "trusted": employer_payload.get("trusted"),
                    }
                )
        return employers

    def _collect_employer_candidates_api(self, search_text: str) -> list[dict[str, object]]:
        merged: dict[str, dict[str, object]] = {}
        for only_with_vacancies in (True, False):
            index_items: list[dict[str, object]] = self._fetch_employers_index(
                search_text=search_text,
                only_with_vacancies=only_with_vacancies,
            )
            merge_employer_items(merged=merged, items=index_items)

        vacancy_items: list[dict[str, object]] = self._fetch_employers_via_vacancies(
            search_text=search_text,
        )
        merge_employer_items(merged=merged, items=vacancy_items)
        return list(merged.values())

    def collect_employer_candidates(self, search_text: str) -> list[dict[str, object]]:
        """Search employers via API, falling back to hh.ru website scraping."""
        result: object = self._call_with_web_fallback(
            api_call=lambda: self._collect_employer_candidates_api(search_text),
            web_call=lambda: self._web().collect_employer_candidates(search_text),
        )
        return cast(list[dict[str, object]], result)

    def list_employer_search_items(self, search_text: str) -> list[dict[str, object]]:
        """Search employers by text and return raw API items."""
        return self.collect_employer_candidates(search_text)

    def search_employer_by_name(self, canonical_name: str) -> tuple[str, str] | None:
        """Search employers by canonical name and return the best match id and name."""
        typed_items: list[dict[str, object]] = self.list_employer_search_items(canonical_name)
        return select_employer_match(canonical_name, typed_items)

    def _fetch_employer_profile_api(self, employer_id: str) -> HhEmployerRating | None:
        profile_params: dict[str, str | int | bool] = {"host": "hh.ru"}
        payload: dict[str, object] = self._get_json(f"/employers/{employer_id}", profile_params)
        return parse_employer_rating(payload)

    def fetch_employer_profile(self, employer_id: str) -> HhEmployerRating | None:
        """Fetch employer profile and parse rating signals when present."""
        result: object = self._call_with_web_fallback(
            api_call=lambda: self._fetch_employer_profile_api(employer_id),
            web_call=lambda: self._web().fetch_employer_profile(employer_id),
        )
        return cast(HhEmployerRating | None, result)

    def _fetch_active_vacancies_api(
        self,
        employer_id: str,
        max_count: int,
    ) -> list[HhVacancyItem]:
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

    def fetch_active_vacancies(self, employer_id: str, max_count: int) -> list[HhVacancyItem]:
        """Fetch active vacancies for an employer, capped at max_count."""
        result: object = self._call_with_web_fallback(
            api_call=lambda: self._fetch_active_vacancies_api(employer_id, max_count),
            web_call=lambda: self._web().fetch_active_vacancies(employer_id, max_count),
        )
        return cast(list[HhVacancyItem], result)

    def fetch_enriched_active_vacancies(
        self,
        employer_id: str,
        max_count: int,
    ) -> list[HhVacancyItem]:
        """Fetch active vacancies and enrich each row with full vacancy detail."""
        if self._use_web:
            return self._web().fetch_enriched_active_vacancies(employer_id, max_count)

        try:
            listed_vacancies: list[HhVacancyItem] = self._fetch_active_vacancies_api(
                employer_id,
                max_count,
            )
        except HhApiBlockedError:
            self._activate_web_fallback()
            return self._web().fetch_enriched_active_vacancies(employer_id, max_count)

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

    def _fetch_vacancy_detail_api(self, vacancy_id: str) -> HhVacancyItem | None:
        detail_params: dict[str, str | int | bool] = {"host": "hh.ru"}
        payload: dict[str, object] = self._get_json(f"/vacancies/{vacancy_id}", detail_params)
        return parse_vacancy_item(payload)

    def fetch_vacancy_detail(self, vacancy_id: str) -> HhVacancyItem | None:
        """Fetch a single vacancy detail payload when enrichment is required."""
        result: object = self._call_with_web_fallback(
            api_call=lambda: self._fetch_vacancy_detail_api(vacancy_id),
            web_call=lambda: self._web().fetch_vacancy_detail(vacancy_id),
        )
        return cast(HhVacancyItem | None, result)
