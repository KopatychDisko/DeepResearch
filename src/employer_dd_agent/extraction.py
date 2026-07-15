from __future__ import annotations

import re
from re import Pattern

from pydantic import AnyHttpUrl

from employer_dd_agent.chunking import chunk_text
from employer_dd_agent.models import (
    CompanyEvent,
    Confidence,
    EventCategory,
    RawFinding,
    SourceType,
)

_CHUNK_SIZE: int = 800
_CHUNK_OVERLAP: int = 120

_DATE_PATTERNS: list[Pattern[str]] = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b"),
]

_CATEGORY_RULES: list[tuple[EventCategory, Pattern[str], Confidence]] = [
    (
        EventCategory.FUNDING,
        re.compile(
            r"(раунд|инвестиц|финансирован|привлекл[аи]?\s+\d|raised\s+\$|funding\s+round)",
            re.IGNORECASE,
        ),
        Confidence.MEDIUM,
    ),
    (
        EventCategory.LEADERSHIP,
        re.compile(
            r"(назначен|сменил[аи]?\s+генеральн|новый\s+ceo|руководств|chief\s+executive)",
            re.IGNORECASE,
        ),
        Confidence.MEDIUM,
    ),
    (
        EventCategory.LAYOFFS,
        re.compile(
            r"(сокращени|увольнен|layoff|сократил[аи]?\s+штат|сокращение\s+штата)",
            re.IGNORECASE,
        ),
        Confidence.MEDIUM,
    ),
    (
        EventCategory.SCANDAL,
        re.compile(
            r"(скандал|расследован|коррупц|нарушени|scandal|investigation)",
            re.IGNORECASE,
        ),
        Confidence.MEDIUM,
    ),
    (
        EventCategory.PRODUCT,
        re.compile(
            r"(запустил[аи]?\s+продукт|релиз|новый\s+сервис|product\s+launch|выпустил[аи]?\s+обновлени)",
            re.IGNORECASE,
        ),
        Confidence.MEDIUM,
    ),
    (
        EventCategory.REVIEW_SIGNAL,
        re.compile(
            r"(отзыв|рейтинг|оценк[аи]\s+сотрудник|employee\s+review|glassdoor)",
            re.IGNORECASE,
        ),
        Confidence.LOW,
    ),
]


def _extract_date_from_text(text: str) -> str | None:
    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            return match.group(1)
    return None


def _build_description(chunk: str, category: EventCategory) -> str:
    normalized_chunk: str = " ".join(chunk.split())
    if len(normalized_chunk) <= 280:
        return normalized_chunk
    return f"{normalized_chunk[:277]}..."


def _extract_events_from_chunk(
    chunk: str,
    source_url: AnyHttpUrl,
    source_type: SourceType,
) -> list[CompanyEvent]:
    events: list[CompanyEvent] = []
    matched_categories: set[EventCategory] = set()

    for category, pattern, confidence in _CATEGORY_RULES:
        if not pattern.search(chunk):
            continue
        if category in matched_categories:
            continue
        if category is EventCategory.REVIEW_SIGNAL and source_type is not SourceType.REVIEWS:
            continue

        matched_categories.add(category)
        events.append(
            CompanyEvent(
                date=_extract_date_from_text(chunk),
                category=category,
                description=_build_description(chunk, category),
                source_url=source_url,
                confidence=confidence,
            )
        )

    return events


def extract_events_from_finding(finding: RawFinding) -> list[CompanyEvent]:
    combined_text: str = f"{finding.title}. {finding.snippet}"
    chunks: list[str] = chunk_text(combined_text, _CHUNK_SIZE, _CHUNK_OVERLAP)

    events: list[CompanyEvent] = []
    for chunk in chunks:
        chunk_events: list[CompanyEvent] = _extract_events_from_chunk(
            chunk,
            finding.source_url,
            finding.source_type,
        )
        events.extend(chunk_events)

    return events


def extract_events_from_findings(findings: list[RawFinding]) -> list[CompanyEvent]:
    all_events: list[CompanyEvent] = []
    for finding in findings:
        finding_events: list[CompanyEvent] = extract_events_from_finding(finding)
        all_events.extend(finding_events)
    return all_events
