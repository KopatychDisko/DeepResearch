from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import AnyHttpUrl

from agents.models import (
    CanonicalTimeline,
    CanonicalTimelineEvent,
    CompanyEvent,
    Confidence,
    EventCategory,
    TimelineConflict,
)

_CONFIDENCE_RANK: dict[Confidence, int] = {
    Confidence.HIGH: 3,
    Confidence.MEDIUM: 2,
    Confidence.LOW: 1,
}

_HIGH_IMPACT_CATEGORIES: set[EventCategory] = {
    EventCategory.FUNDING,
    EventCategory.LAYOFFS,
    EventCategory.SCANDAL,
    EventCategory.LEADERSHIP,
}


def _normalize_signature_text(text: str) -> str:
    lowered: str = text.lower()
    alphanumeric: str = re.sub(r"[^a-zа-яё0-9\s]", " ", lowered, flags=re.IGNORECASE)
    collapsed: str = re.sub(r"\s+", " ", alphanumeric).strip()
    return collapsed[:160]


def _event_signature(event: CompanyEvent) -> str:
    normalized_description: str = _normalize_signature_text(event.description)
    return f"{event.category.value}|{normalized_description}"


_RUSSIAN_MONTHS: dict[str, int] = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def _is_missing_date(date_value: str | None) -> bool:
    if date_value is None:
        return True
    normalized: str = date_value.strip().lower()
    return normalized in {"", "null", "none", "unknown", "n/a", "неизвестно"}


def _parse_sortable_date(date_value: str | None) -> date | None:
    if _is_missing_date(date_value):
        return None

    assert date_value is not None

    iso_match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", date_value)
    if iso_match is not None:
        return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))

    year_month_match = re.fullmatch(r"(\d{4})-(\d{2})", date_value)
    if year_month_match is not None:
        return date(int(year_month_match.group(1)), int(year_month_match.group(2)), 1)

    dotted_match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", date_value)
    if dotted_match is not None:
        return date(
            int(dotted_match.group(3)),
            int(dotted_match.group(2)),
            int(dotted_match.group(1)),
        )

    named_month_formats: list[str] = [
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]
    for date_format in named_month_formats:
        try:
            return datetime.strptime(date_value, date_format).date()
        except ValueError:
            continue

    month_year_formats: list[str] = [
        "%B %Y",
        "%b %Y",
    ]
    for date_format in month_year_formats:
        try:
            return datetime.strptime(date_value, date_format).date()
        except ValueError:
            continue

    russian_match = re.fullmatch(
        r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})",
        date_value.lower(),
        flags=re.IGNORECASE,
    )
    if russian_match is not None:
        month_name: str = russian_match.group(2).lower()
        if month_name not in _RUSSIAN_MONTHS:
            raise ValueError(f"Unsupported Russian month in date: {date_value}")
        return date(
            int(russian_match.group(3)),
            _RUSSIAN_MONTHS[month_name],
            int(russian_match.group(1)),
        )

    russian_month_year_match = re.fullmatch(
        r"([а-яё]+)\s+(\d{4})",
        date_value.lower(),
        flags=re.IGNORECASE,
    )
    if russian_month_year_match is not None:
        month_name = russian_month_year_match.group(1).lower()
        if month_name not in _RUSSIAN_MONTHS:
            raise ValueError(f"Unsupported Russian month in date: {date_value}")
        return date(
            int(russian_month_year_match.group(2)),
            _RUSSIAN_MONTHS[month_name],
            1,
        )

    raise ValueError(f"Unsupported date format for sorting: {date_value}")


def _pick_highest_confidence(confidences: list[Confidence]) -> Confidence:
    if not confidences:
        raise ValueError("confidences must not be empty")
    return max(confidences, key=lambda confidence: _CONFIDENCE_RANK[confidence])


def _pick_canonical_description(descriptions: list[str]) -> str:
    if not descriptions:
        raise ValueError("descriptions must not be empty")
    return max(descriptions, key=len)


def _collect_unique_source_urls(events: list[CompanyEvent]) -> list[AnyHttpUrl]:
    seen_urls: set[str] = set()
    unique_urls: list[AnyHttpUrl] = []
    for event in events:
        url_text: str = str(event.source_url)
        if url_text in seen_urls:
            continue
        seen_urls.add(url_text)
        unique_urls.append(event.source_url)
    return unique_urls


def _build_date_conflict(
    category: EventCategory,
    events: list[CompanyEvent],
    source_urls: list[AnyHttpUrl],
) -> TimelineConflict | None:
    distinct_dates: list[str] = []
    for event in events:
        if event.date is None:
            continue
        if event.date not in distinct_dates:
            distinct_dates.append(event.date)

    if len(distinct_dates) <= 1:
        return None

    if category not in _HIGH_IMPACT_CATEGORIES:
        return None

    return TimelineConflict(
        category=category,
        message=(
            f"Sources disagree on date for {category.value}: "
            f"{', '.join(distinct_dates)}"
        ),
        source_urls=source_urls,
        dates=distinct_dates,
    )


def _merge_event_cluster(events: list[CompanyEvent]) -> tuple[CanonicalTimelineEvent, TimelineConflict | None]:
    if not events:
        raise ValueError("events cluster must not be empty")

    source_urls: list[AnyHttpUrl] = _collect_unique_source_urls(events)
    confidences: list[Confidence] = [event.confidence for event in events]
    descriptions: list[str] = [event.description for event in events]
    category: EventCategory = events[0].category

    distinct_dates: list[str] = []
    for event in events:
        if event.date is None:
            continue
        if event.date not in distinct_dates:
            distinct_dates.append(event.date)

    canonical_date: str | None = None
    has_date_conflict: bool = False
    if len(distinct_dates) == 1:
        canonical_date = distinct_dates[0]
    elif len(distinct_dates) > 1:
        has_date_conflict = True
        canonical_date = distinct_dates[0]

    conflict: TimelineConflict | None = _build_date_conflict(category, events, source_urls)

    canonical_event: CanonicalTimelineEvent = CanonicalTimelineEvent(
        date=canonical_date,
        category=category,
        description=_pick_canonical_description(descriptions),
        source_urls=source_urls,
        confidence=_pick_highest_confidence(confidences),
        has_date_conflict=has_date_conflict,
    )
    return canonical_event, conflict


def _sort_timeline_events(events: list[CanonicalTimelineEvent]) -> list[CanonicalTimelineEvent]:
    dated_events: list[tuple[date, CanonicalTimelineEvent]] = []
    undated_events: list[CanonicalTimelineEvent] = []

    for event in events:
        if _is_missing_date(event.date):
            undated_events.append(event)
            continue
        sortable_date: date | None = _parse_sortable_date(event.date)
        if sortable_date is None:
            undated_events.append(event)
            continue
        dated_events.append((sortable_date, event))

    dated_events.sort(key=lambda item: item[0], reverse=True)
    sorted_events: list[CanonicalTimelineEvent] = [item[1] for item in dated_events]
    sorted_events.extend(undated_events)
    return sorted_events


def merge_events_into_timeline(events: list[CompanyEvent]) -> CanonicalTimeline:
    clusters: dict[str, list[CompanyEvent]] = {}
    cluster_order: list[str] = []

    for event in events:
        signature: str = _event_signature(event)
        if signature not in clusters:
            clusters[signature] = []
            cluster_order.append(signature)
        clusters[signature].append(event)

    canonical_events: list[CanonicalTimelineEvent] = []
    conflicts: list[TimelineConflict] = []

    for signature in cluster_order:
        cluster_events: list[CompanyEvent] = clusters[signature]
        canonical_event, conflict = _merge_event_cluster(cluster_events)
        canonical_events.append(canonical_event)
        if conflict is not None:
            conflicts.append(conflict)

    sorted_events: list[CanonicalTimelineEvent] = _sort_timeline_events(canonical_events)
    return CanonicalTimeline(events=sorted_events, conflicts=conflicts)
