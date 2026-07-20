"""HH.ru API runtime preflight checks."""

from __future__ import annotations

import os
import re

from agents.configuration import Configuration

HH_API_PLACEHOLDER_USER_AGENT: str = "EmployerDD/1.0 (contact@example.com)"
HH_API_USER_AGENT_ENV: str = "HH_API_USER_AGENT"
HH_API_SETUP_MESSAGE: str = (
    "HH.ru API requires a registered User-Agent. Register an app at https://dev.hh.ru/ "
    f"and set {HH_API_USER_AGENT_ENV} in .env "
    '(format: "AppName/1.0 (you@email.com)").'
)
CONTACT_IN_USER_AGENT_PATTERN: re.Pattern[str] = re.compile(r"\(([^)]+)\)")


def _contact_token_in_user_agent(user_agent: str) -> str | None:
    match = CONTACT_IN_USER_AGENT_PATTERN.search(user_agent)
    if match is None:
        return None
    contact_token: str = match.group(1).strip()
    if contact_token == "":
        return None
    return contact_token


def is_hh_api_user_agent_configured(settings: Configuration) -> bool:
    """Return True when HH_API_USER_AGENT is explicitly set with a real contact."""
    env_value: str | None = os.environ.get(HH_API_USER_AGENT_ENV)
    if env_value is None or env_value.strip() == "":
        return False
    user_agent: str = settings.hh_api_user_agent.strip()
    if user_agent == "" or user_agent == HH_API_PLACEHOLDER_USER_AGENT:
        return False
    contact_token: str | None = _contact_token_in_user_agent(user_agent=user_agent)
    if contact_token is None:
        return False
    if contact_token.lower() in {"contact@example.com", "your_email@example.com"}:
        return False
    if "@" in contact_token:
        return True
    return len(contact_token) >= 5


def require_hh_api_user_agent(settings: Configuration) -> None:
    """Raise RuntimeError when HH API User-Agent is missing or invalid."""
    if is_hh_api_user_agent_configured(settings=settings):
        return
    raise RuntimeError(HH_API_SETUP_MESSAGE)
