from __future__ import annotations

import re
from datetime import datetime
from typing import TypedDict

from pydantic import AnyHttpUrl

from agents.models import CompanyEvent, EventCategory, RawFinding, RetrievalMetadata, SourceType
from agents.structure_events.extraction import extract_events_from_finding
from tests.eval_common import load_golden_dataset

_ISO_DATE_PATTERN: re.Pattern[str] = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RU_DATE_PATTERN: re.Pattern[str] = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")


class ExpectedEvent(TypedDict, total=False):
    category: str
    date: str
    confidence: str
    description_contains: str


class StructureEventsGoldenFinding(TypedDict):
    source_type: str
    source_url: str
    title: str
    snippet: str
    metadata: dict[str, str]


class StructureEventsGoldenCase(TypedDict):
    id: str
    finding: StructureEventsGoldenFinding
    expected_event_count: int
    expected_events: list[ExpectedEvent]


def load_structure_events_golden_cases() -> list[StructureEventsGoldenCase]:
    raw_cases: list[dict[str, object]] = load_golden_dataset("structure_events_golden")
    typed_cases: list[StructureEventsGoldenCase] = []
    for raw_case in raw_cases:
        if "id" not in raw_case or not isinstance(raw_case["id"], str):
            raise TypeError("Each structure_events golden case must have a string id")
        if "finding" not in raw_case or not isinstance(raw_case["finding"], dict):
            raise TypeError(f"Case {raw_case['id']} must have a finding object")
        if "expected_event_count" not in raw_case or not isinstance(
            raw_case["expected_event_count"], int
        ):
            raise TypeError(f"Case {raw_case['id']} must have an integer expected_event_count")
        if "expected_events" not in raw_case or not isinstance(raw_case["expected_events"], list):
            raise TypeError(f"Case {raw_case['id']} must have an expected_events list")
        for expected_event in raw_case["expected_events"]:
            if not isinstance(expected_event, dict):
                raise TypeError(f"Case {raw_case['id']} expected_events must contain objects")
            if "category" not in expected_event or not isinstance(expected_event["category"], str):
                raise TypeError(
                    f"Case {raw_case['id']} expected_events must have string category"
                )
        typed_cases.append(raw_case)  # type: ignore[arg-type]
    return typed_cases


def build_raw_finding(case: StructureEventsGoldenCase) -> RawFinding:
    finding_data: StructureEventsGoldenFinding = case["finding"]
    metadata_raw: dict[str, str] = finding_data["metadata"]
    if "fetched_at" not in metadata_raw:
        raise ValueError(f"Case {case['id']} finding metadata must include fetched_at")
    if "source_label" not in metadata_raw:
        raise ValueError(f"Case {case['id']} finding metadata must include source_label")
    if "note" not in metadata_raw:
        raise ValueError(f"Case {case['id']} finding metadata must include note")
    fetched_at: datetime = datetime.fromisoformat(metadata_raw["fetched_at"])
    return RawFinding(
        source_type=SourceType(finding_data["source_type"]),
        source_url=AnyHttpUrl(finding_data["source_url"]),
        title=finding_data["title"],
        snippet=finding_data["snippet"],
        metadata=RetrievalMetadata(
            fetched_at=fetched_at,
            source_label=metadata_raw["source_label"],
            note=metadata_raw["note"],
        ),
    )


def extract_events_from_golden(case: StructureEventsGoldenCase) -> list[CompanyEvent]:
    finding: RawFinding = build_raw_finding(case=case)
    return extract_events_from_finding(finding)


def _normalize_date(date_value: str) -> str:
    if _ISO_DATE_PATTERN.match(date_value):
        return date_value
    ru_match: re.Match[str] | None = _RU_DATE_PATTERN.match(date_value)
    if ru_match is None:
        raise ValueError(f"Unsupported date format: {date_value}")
    day: str = ru_match.group(1).zfill(2)
    month: str = ru_match.group(2).zfill(2)
    year: str = ru_match.group(3)
    return f"{year}-{month}-{day}"


def _actual_categories(events: list[CompanyEvent]) -> set[str]:
    return {event.category.value for event in events}


def _expected_categories(case: StructureEventsGoldenCase) -> set[str]:
    return {expected_event["category"] for expected_event in case["expected_events"]}


def category_detection_score(
    case: StructureEventsGoldenCase,
    events: list[CompanyEvent],
) -> float:
    if _actual_categories(events=events) != _expected_categories(case=case):
        return 0.0
    return 1.0


def date_extraction_score(
    case: StructureEventsGoldenCase,
    events: list[CompanyEvent],
) -> float:
    events_by_category: dict[str, list[CompanyEvent]] = {}
    for event in events:
        category_key: str = event.category.value
        if category_key not in events_by_category:
            events_by_category[category_key] = []
        events_by_category[category_key].append(event)

    for expected_event in case["expected_events"]:
        if "date" not in expected_event:
            continue
        category_key = expected_event["category"]
        if category_key not in events_by_category:
            return 0.0
        expected_normalized: str = _normalize_date(expected_event["date"])
        matched_date: bool = False
        for actual_event in events_by_category[category_key]:
            if actual_event.date is None:
                continue
            actual_normalized: str = _normalize_date(actual_event.date)
            if actual_normalized == expected_normalized:
                matched_date = True
                break
        if not matched_date:
            return 0.0
    return 1.0


def event_count_score(
    case: StructureEventsGoldenCase,
    events: list[CompanyEvent],
) -> float:
    if len(events) != case["expected_event_count"]:
        return 0.0
    return 1.0
