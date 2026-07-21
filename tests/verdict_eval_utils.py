from __future__ import annotations

from typing import NotRequired, TypedDict

from pydantic import AnyHttpUrl

from agents.models import (
    CanonicalTimeline,
    CanonicalTimelineEvent,
    Confidence,
    EventCategory,
    ResponseLanguage,
    TimelineConflict,
)
from agents.verdict.verdict import (
    build_evidence_links,
    build_red_flags_from_timeline,
    build_risks_from_timeline,
)
from tests.eval_common import load_golden_dataset


class VerdictGoldenEvent(TypedDict):
    date: str
    category: str
    description: str
    source_urls: list[str]
    confidence: str
    has_date_conflict: bool


class VerdictGoldenConflict(TypedDict):
    category: str
    message: str
    source_urls: list[str]
    dates: list[str]


class VerdictGoldenTimeline(TypedDict):
    events: list[VerdictGoldenEvent]
    conflicts: list[VerdictGoldenConflict]


class VerdictGoldenCase(TypedDict):
    id: str
    timeline: VerdictGoldenTimeline
    language: str
    expected_red_flag_count: int
    expected_risk_count: int
    expected_red_flag_substrings: NotRequired[list[str]]
    expected_risk_substrings: NotRequired[list[str]]


def _parse_event_category(category_value: str, case_id: str) -> EventCategory:
    try:
        return EventCategory(category_value)
    except ValueError as error:
        raise ValueError(
            f"Case {case_id} has unknown event category: {category_value}"
        ) from error


def load_verdict_golden_cases() -> list[VerdictGoldenCase]:
    raw_cases: list[dict[str, object]] = load_golden_dataset("verdict_golden")
    typed_cases: list[VerdictGoldenCase] = []
    for raw_case in raw_cases:
        if "id" not in raw_case or not isinstance(raw_case["id"], str):
            raise TypeError("Each verdict golden case must have a string id")
        if "timeline" not in raw_case or not isinstance(raw_case["timeline"], dict):
            raise TypeError(f"Case {raw_case['id']} must have a timeline object")
        if "language" not in raw_case or not isinstance(raw_case["language"], str):
            raise TypeError(f"Case {raw_case['id']} must have a language string")
        if "expected_red_flag_count" not in raw_case or not isinstance(
            raw_case["expected_red_flag_count"], int
        ):
            raise TypeError(f"Case {raw_case['id']} must have expected_red_flag_count")
        if "expected_risk_count" not in raw_case or not isinstance(
            raw_case["expected_risk_count"], int
        ):
            raise TypeError(f"Case {raw_case['id']} must have expected_risk_count")
        typed_cases.append(raw_case)  # type: ignore[arg-type]
    return typed_cases


def build_timeline(case: VerdictGoldenCase) -> CanonicalTimeline:
    timeline_data: VerdictGoldenTimeline = case["timeline"]
    events: list[CanonicalTimelineEvent] = []
    for event_data in timeline_data["events"]:
        category: EventCategory = _parse_event_category(
            category_value=event_data["category"],
            case_id=case["id"],
        )
        events.append(
            CanonicalTimelineEvent(
                date=event_data["date"],
                category=category,
                description=event_data["description"],
                source_urls=[AnyHttpUrl(url) for url in event_data["source_urls"]],
                confidence=Confidence(event_data["confidence"]),
                has_date_conflict=event_data["has_date_conflict"],
            )
        )
    conflicts: list[TimelineConflict] = []
    for conflict_data in timeline_data["conflicts"]:
        conflict_category: EventCategory = _parse_event_category(
            category_value=conflict_data["category"],
            case_id=case["id"],
        )
        conflicts.append(
            TimelineConflict(
                category=conflict_category,
                message=conflict_data["message"],
                source_urls=[AnyHttpUrl(url) for url in conflict_data["source_urls"]],
                dates=conflict_data["dates"],
            )
        )
    return CanonicalTimeline(events=events, conflicts=conflicts)


def _response_language(case: VerdictGoldenCase) -> ResponseLanguage:
    return ResponseLanguage(case["language"])


def score_red_flags(case: VerdictGoldenCase, timeline: CanonicalTimeline) -> float:
    language: ResponseLanguage = _response_language(case=case)
    red_flags: list[str] = build_red_flags_from_timeline(
        timeline=timeline,
        language=language,
    )
    if len(red_flags) != case["expected_red_flag_count"]:
        return 0.0
    if "expected_red_flag_substrings" in case:
        for substring in case["expected_red_flag_substrings"]:
            if not any(substring in flag for flag in red_flags):
                return 0.0
    return 1.0


def score_risks(case: VerdictGoldenCase, timeline: CanonicalTimeline) -> float:
    language: ResponseLanguage = _response_language(case=case)
    risks: list[str] = build_risks_from_timeline(
        timeline=timeline,
        language=language,
    )
    if len(risks) != case["expected_risk_count"]:
        return 0.0
    if "expected_risk_substrings" in case:
        for substring in case["expected_risk_substrings"]:
            if not any(substring in risk for risk in risks):
                return 0.0
    return 1.0


def score_evidence_links(case: VerdictGoldenCase, timeline: CanonicalTimeline) -> float:
    evidence_links = build_evidence_links(timeline=timeline)
    if len(evidence_links) != len(timeline.events):
        return 0.0
    return 1.0
