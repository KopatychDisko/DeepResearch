"""Tests for hh.ru HTML stripping and User-Agent validation."""

from __future__ import annotations

import pytest

from agents.configuration import Configuration
from agents.hh_vacancies.html_utils import strip_html
from agents.hh_vacancies.runtime import is_hh_api_user_agent_configured, require_hh_api_user_agent


def test_strip_html_removes_tags_and_collapses_blank_lines() -> None:
    raw_html: str = "<p>Backend role</p><ul><li>Python</li></ul>"
    assert strip_html(raw_html) == "Backend role\nPython"


def test_user_agent_with_empty_contact_is_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HH_API_USER_AGENT", 'EmployerDueDiligence/1.0 ()')
    settings = Configuration(hh_api_user_agent='EmployerDueDiligence/1.0 ()')
    assert is_hh_api_user_agent_configured(settings=settings) is False
    with pytest.raises(RuntimeError, match="HH.ru API requires a registered User-Agent"):
        require_hh_api_user_agent(settings=settings)


def test_user_agent_with_email_contact_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HH_API_USER_AGENT", "VacancyIntelAgent/1.0 (dev@example.com)")
    settings = Configuration(hh_api_user_agent="VacancyIntelAgent/1.0 (dev@example.com)")
    assert is_hh_api_user_agent_configured(settings=settings) is True
