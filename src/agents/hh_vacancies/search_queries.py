"""Build hh.ru employer search query variants from resolved company identity."""

from __future__ import annotations

import re

from agents.models import CompanyIdentity

PARENTHETICAL_PATTERN: re.Pattern[str] = re.compile(r"\([^)]*\)")
SPLIT_PATTERN: re.Pattern[str] = re.compile(r"[/|,;]+")


def _append_unique(queries: list[str], seen: set[str], value: str) -> None:
    cleaned: str = " ".join(value.split())
    if cleaned == "":
        return
    normalized_key: str = cleaned.casefold()
    if normalized_key in seen:
        return
    seen.add(normalized_key)
    queries.append(cleaned)


def extract_employer_search_queries(
    identity: CompanyIdentity,
    search_query_override: str | None,
) -> list[str]:
    """Return ordered unique employer name variants to try on api.hh.ru."""
    queries: list[str] = []
    seen: set[str] = set()

    if search_query_override is not None:
        override: str = search_query_override.strip()
        if override == "":
            raise ValueError("search_query_override must not be empty")
        _append_unique(queries, seen, override)
        _append_variants_from_name(queries, seen, override)
        return queries

    _append_unique(queries, seen, identity.canonical_name)
    if identity.query_name != identity.canonical_name:
        _append_unique(queries, seen, identity.query_name)

    _append_variants_from_name(queries, seen, identity.canonical_name)
    if identity.query_name != identity.canonical_name:
        _append_variants_from_name(queries, seen, identity.query_name)

    return queries


def _append_variants_from_name(
    queries: list[str],
    seen: set[str],
    name: str,
) -> None:
    without_parens: str = PARENTHETICAL_PATTERN.sub("", name).strip()
    _append_unique(queries, seen, without_parens)

    for match in re.finditer(r"\(([^)]+)\)", name):
        inner_text: str = match.group(1)
        for part in SPLIT_PATTERN.split(inner_text):
            _append_unique(queries, seen, part)

    for part in SPLIT_PATTERN.split(name):
        cleaned_part: str = PARENTHETICAL_PATTERN.sub("", part).strip()
        _append_unique(queries, seen, cleaned_part)
