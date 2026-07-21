from __future__ import annotations

import pytest

from tests.structure_events_eval_utils import (
    StructureEventsGoldenCase,
    category_detection_score,
    date_extraction_score,
    event_count_score,
    extract_events_from_golden,
    load_structure_events_golden_cases,
)


@pytest.mark.parametrize(
    "case",
    load_structure_events_golden_cases(),
    ids=lambda case: case["id"],
)
def test_structure_events_golden_case(case: StructureEventsGoldenCase) -> None:
    events = extract_events_from_golden(case=case)
    assert category_detection_score(case=case, events=events) == 1.0, (
        f"category detection failed for case={case['id']}"
    )
    assert date_extraction_score(case=case, events=events) == 1.0, (
        f"date extraction failed for case={case['id']}"
    )
    assert event_count_score(case=case, events=events) == 1.0, (
        f"event count failed for case={case['id']}"
    )
