from __future__ import annotations

from tests.merge_eval_utils import (
    conflict_accuracy_score,
    date_fact_accuracy_score,
    dedup_precision_score,
    dedup_recall_score,
    load_merge_golden_cases,
    merge_case,
)


def test_merge_golden_dedup_recall() -> None:
    for case in load_merge_golden_cases():
        timeline = merge_case(case=case)
        score: float = dedup_recall_score(case=case, timeline=timeline)
        assert score >= 0.99, f"dedup recall failed for case={case['id']} score={score}"


def test_merge_golden_dedup_precision() -> None:
    for case in load_merge_golden_cases():
        timeline = merge_case(case=case)
        score: float = dedup_precision_score(case=case, timeline=timeline)
        assert score == 1.0, f"dedup precision failed for case={case['id']}"


def test_merge_golden_date_fact_accuracy() -> None:
    for case in load_merge_golden_cases():
        if "expected_date" not in case and "expected_first_date" not in case:
            continue
        timeline = merge_case(case=case)
        score: float = date_fact_accuracy_score(case=case, timeline=timeline)
        assert score == 1.0, f"date/fact accuracy failed for case={case['id']}"


def test_merge_golden_conflict_detection() -> None:
    for case in load_merge_golden_cases():
        timeline = merge_case(case=case)
        score: float = conflict_accuracy_score(case=case, timeline=timeline)
        assert score == 1.0, f"conflict detection failed for case={case['id']}"


def test_merge_source_url_aggregation() -> None:
    for case in load_merge_golden_cases():
        timeline = merge_case(case=case)
        if len(timeline.events) != 1:
            continue
        assert (
            len(timeline.events[0].source_urls) == case["expected_source_url_count"]
        ), f"source url aggregation failed for case={case['id']}"
