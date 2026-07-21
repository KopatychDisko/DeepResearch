from __future__ import annotations

import json
from pathlib import Path
from typing import NotRequired, TypedDict

from agents.merge.merge import merge_events_into_timeline
from agents.models import (
    CanonicalTimeline,
    CompanyEvent,
    Confidence,
    EventCategory,
)


class MergeGoldenCase(TypedDict):
    id: str
    input_events: list[dict[str, str | None]]
    expected_canonical_count: int
    expected_source_url_count: int
    expected_conflicts: int
    expected_has_date_conflict: bool
    expected_confidence: NotRequired[str]
    expected_date: NotRequired[str]
    expected_first_date: NotRequired[str]


def load_merge_golden_cases() -> list[MergeGoldenCase]:
    dataset_path: Path = (
        Path(__file__).resolve().parents[1] / "eval" / "datasets" / "merge_golden.json"
    )
    raw_cases: object = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list):
        raise TypeError("merge_golden.json must contain a list of cases")
    typed_cases: list[MergeGoldenCase] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise TypeError("Each merge golden case must be an object")
        typed_cases.append(raw_case)  # type: ignore[arg-type]
    return typed_cases


def build_company_events(case: MergeGoldenCase) -> list[CompanyEvent]:
    events: list[CompanyEvent] = []
    for raw_event in case["input_events"]:
        events.append(
            CompanyEvent(
                date=raw_event.get("date"),
                category=EventCategory(str(raw_event["category"])),
                description=str(raw_event["description"]),
                source_url=raw_event["source_url"],  # type: ignore[arg-type]
                confidence=Confidence(str(raw_event["confidence"])),
            )
        )
    return events


def merge_case(case: MergeGoldenCase) -> CanonicalTimeline:
    return merge_events_into_timeline(build_company_events(case=case))


def dedup_recall_score(case: MergeGoldenCase, timeline: CanonicalTimeline) -> float:
    input_count: int = len(case["input_events"])
    if input_count == 0:
        return 1.0
    merged_ratio: float = len(timeline.events) / input_count
    if merged_ratio > case["expected_canonical_count"] / input_count:
        return case["expected_canonical_count"] / len(timeline.events)
    return 1.0


def dedup_precision_score(case: MergeGoldenCase, timeline: CanonicalTimeline) -> float:
    if len(timeline.events) != case["expected_canonical_count"]:
        return 0.0
    return 1.0


def date_fact_accuracy_score(case: MergeGoldenCase, timeline: CanonicalTimeline) -> float:
    if "expected_date" in case:
        if len(timeline.events) != 1:
            return 0.0
        if timeline.events[0].date != case["expected_date"]:
            return 0.0
        if timeline.events[0].confidence.value != case["expected_confidence"]:
            return 0.0
        return 1.0
    if "expected_first_date" in case:
        if len(timeline.events) < 1:
            return 0.0
        if timeline.events[0].date != case["expected_first_date"]:
            return 0.0
        return 1.0
    return 1.0


def conflict_accuracy_score(case: MergeGoldenCase, timeline: CanonicalTimeline) -> float:
    if len(timeline.conflicts) != case["expected_conflicts"]:
        return 0.0
    if len(timeline.events) == 0:
        return 1.0
    if timeline.events[0].has_date_conflict != case["expected_has_date_conflict"]:
        return 0.0
    return 1.0
