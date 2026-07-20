"""Tests for hh.ru website scraper parsing helpers."""

from __future__ import annotations

from agents.hh_vacancies.web_scraper import (
    extract_employers_from_vacancy_search,
    flatten_employers_list,
    parse_web_compensation,
    parse_web_vacancy_detail_view,
    parse_web_vacancy_search_item,
)


def test_parse_web_compensation_maps_currency_code() -> None:
    salary = parse_web_compensation(
        {"from": 100000, "to": 150000, "currencyCode": "RUR", "gross": True}
    )
    assert salary is not None
    assert salary.from_amount == 100000
    assert salary.to_amount == 150000
    assert salary.currency == "RUR"
    assert salary.gross is True


def test_flatten_employers_list_groups_by_letter() -> None:
    state: dict[str, object] = {
        "employersList": {
            "employers": {
                "с": [
                    {"id": 3529, "name": "СБЕР", "vacanciesOpen": 3700},
                    {"id": 829010, "name": "Сбер Банк", "vacanciesOpen": 43},
                ]
            }
        }
    }
    employers = flatten_employers_list(state)
    assert len(employers) == 2
    assert employers[0]["id"] == "3529"
    assert employers[0]["name"] == "СБЕР"


def test_extract_employers_from_vacancy_search_deduplicates_companies() -> None:
    state: dict[str, object] = {
        "vacancySearchResult": {
            "vacancies": [
                {
                    "vacancyId": 1,
                    "name": "Role A",
                    "company": {"id": 3529, "name": "СБЕР", "@trusted": True},
                },
                {
                    "vacancyId": 2,
                    "name": "Role B",
                    "company": {"id": 3529, "name": "СБЕР", "@trusted": True},
                },
            ]
        }
    }
    employers = extract_employers_from_vacancy_search(state)
    assert len(employers) == 1
    assert employers[0]["id"] == "3529"


def test_parse_web_vacancy_search_item_maps_core_fields() -> None:
    vacancy = parse_web_vacancy_search_item(
        {
            "vacancyId": 135094073,
            "name": "Python Developer",
            "area": {"name": "Москва"},
            "compensation": {"from": 200000, "currencyCode": "RUR", "gross": True},
            "employmentForm": "FULL",
            "workExperience": "От 3 до 6 лет",
            "publicationTime": "2026-07-15T10:00:00+0300",
            "company": {"id": 3529, "name": "СБЕР", "@trusted": True},
        }
    )
    assert vacancy.vacancy_id == "135094073"
    assert vacancy.title == "Python Developer"
    assert vacancy.area_name == "Москва"
    assert vacancy.employer_trusted is True
    assert vacancy.salary is not None
    assert vacancy.salary.from_amount == 200000


def test_parse_web_vacancy_detail_view_strips_description_html() -> None:
    vacancy = parse_web_vacancy_detail_view(
        {
            "vacancyId": 135094073,
            "name": "Python Developer",
            "area": {"name": "Москва"},
            "compensation": {"from": 200000, "currencyCode": "RUR", "gross": True},
            "employmentForm": "FULL",
            "workExperience": "От 3 до 6 лет",
            "publicationDate": "2026-07-15T10:00:00+0300",
            "description": "<p>Backend role</p><ul><li>Python</li></ul>",
            "keySkills": {"keySkill": ["Python", "FastAPI"]},
            "company": {"id": 3529, "name": "СБЕР", "@trusted": True},
            "status": "open",
        }
    )
    assert vacancy.description_plain == "Backend role\nPython"
    assert vacancy.key_skills == ["Python", "FastAPI"]
    assert vacancy.archived is False
