"""Parse and normalize hh.ru API JSON payloads."""

from __future__ import annotations

import re

from agents.hh_vacancies.html_utils import strip_html
from agents.models import HhEmployerRating, HhSalaryRange, HhVacancyItem

LEGAL_SUFFIX_PATTERN: re.Pattern[str] = re.compile(
    r"\b(ооо|ао|пао|зао|оао|llc|ltd|inc)\b",
    re.IGNORECASE,
)
PUNCTUATION_PATTERN: re.Pattern[str] = re.compile(r"[^\w\s]", re.UNICODE)
PARENTHETICAL_PATTERN: re.Pattern[str] = re.compile(r"\([^)]*\)")


def normalize_employer_name(name: str) -> str:
    """Normalize employer names for exact and fuzzy matching."""
    lowered_name: str = name.casefold().strip()
    without_parens: str = PARENTHETICAL_PATTERN.sub(" ", lowered_name)
    without_punct: str = PUNCTUATION_PATTERN.sub(" ", without_parens)
    without_suffix: str = LEGAL_SUFFIX_PATTERN.sub("", without_punct)
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


def employer_match_score(query_name: str, employer_name: str) -> float:
    """Score how well an hh.ru employer name matches the resolved company name."""
    normalized_query: str = normalize_employer_name(query_name)
    normalized_employer: str = normalize_employer_name(employer_name)
    if normalized_query == normalized_employer:
        return 1.0
    if normalized_query == "" or normalized_employer == "":
        return 0.0
    if normalized_query in normalized_employer or normalized_employer in normalized_query:
        return 0.9
    return token_overlap_score(query_name, employer_name)


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


def parse_key_skills(payload: object) -> list[str]:
    """Extract skill names from hh.ru key_skills payload."""
    if not isinstance(payload, list):
        return []
    skills: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name_value = item.get("name")
        if isinstance(name_value, str) and name_value.strip() != "":
            skills.append(name_value.strip())
    return skills


def named_labels(payload_items: object) -> list[str]:
    """Extract display names from a list of hh.ru labeled objects."""
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
    working_conditions.extend(named_labels(vacancy_payload.get("working_days")))
    working_conditions.extend(named_labels(vacancy_payload.get("working_time_modes")))

    published_at_value = vacancy_payload.get("published_at")
    published_at: str | None = published_at_value if isinstance(published_at_value, str) else None

    archived_value = vacancy_payload.get("archived")
    archived: bool | None = archived_value if isinstance(archived_value, bool) else None

    description_value = vacancy_payload.get("description")
    description_plain: str | None = None
    if isinstance(description_value, str) and description_value.strip() != "":
        description_plain = strip_html(description_value)

    key_skills: list[str] = parse_key_skills(vacancy_payload.get("key_skills"))

    employer_payload = vacancy_payload.get("employer")
    employer_trusted: bool | None = None
    if isinstance(employer_payload, dict):
        trusted_value = employer_payload.get("trusted")
        if isinstance(trusted_value, bool):
            employer_trusted = trusted_value

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
        archived=archived,
        key_skills=key_skills,
        description_plain=description_plain,
        employer_trusted=employer_trusted,
    )


def parse_employer_rating(profile_payload: dict[str, object]) -> HhEmployerRating:
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


def select_employer_match(
    canonical_name: str,
    items: list[dict[str, object]],
) -> tuple[str, str] | None:
    """Pick the best employer id and name from search results."""
    if not items:
        return None

    best_match: tuple[str, str] | None = None
    best_score: float = 0.0
    for item in items:
        employer_id_value = item.get("id")
        employer_name_value = item.get("name")
        if not isinstance(employer_id_value, (str, int)) or not isinstance(employer_name_value, str):
            continue
        score: float = employer_match_score(canonical_name, employer_name_value)
        if score <= 0.0:
            continue
        if best_match is None or score > best_score:
            best_score = score
            best_match = (str(employer_id_value), employer_name_value)

    return best_match


def merge_employer_items(
    merged: dict[str, dict[str, object]],
    items: list[dict[str, object]],
) -> None:
    """Merge employer search items into a dict keyed by employer id."""
    for item in items:
        employer_id_value = item.get("id")
        if not isinstance(employer_id_value, (str, int)):
            continue
        merged[str(employer_id_value)] = item
