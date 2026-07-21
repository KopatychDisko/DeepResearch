from __future__ import annotations

import json

import pytest
from deepeval import assert_test
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from tests.eval_common import EvalQualityMetric
from tests.structure_events_eval_utils import (
    StructureEventsGoldenCase,
    category_detection_score,
    date_extraction_score,
    event_count_score,
    extract_events_from_golden,
    load_structure_events_golden_cases,
)

pytestmark = pytest.mark.eval


class CategoryDetectionMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "Category Detection"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[StructureEventsGoldenCase] = load_structure_events_golden_cases()
        selected_case: StructureEventsGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        events = extract_events_from_golden(case=selected_case)
        self.score = category_detection_score(case=selected_case, events=events)
        self.success = self.score >= self.threshold
        return self.score


class DateExtractionMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "Date Extraction"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[StructureEventsGoldenCase] = load_structure_events_golden_cases()
        selected_case: StructureEventsGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        events = extract_events_from_golden(case=selected_case)
        self.score = date_extraction_score(case=selected_case, events=events)
        self.success = self.score >= self.threshold
        return self.score


class EventCountMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "Event Count"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[StructureEventsGoldenCase] = load_structure_events_golden_cases()
        selected_case: StructureEventsGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        events = extract_events_from_golden(case=selected_case)
        self.score = event_count_score(case=selected_case, events=events)
        self.success = self.score >= self.threshold
        return self.score


@pytest.mark.parametrize(
    "case",
    load_structure_events_golden_cases(),
    ids=lambda case: case["id"],
)
def test_deepeval_structure_events(case: StructureEventsGoldenCase) -> None:
    test_case = LLMTestCase(
        input=json.dumps({"case_id": case["id"]}),
        actual_output="structure_events_pipeline_output",
        expected_output="structure_events_pipeline_expected",
    )
    metrics: list[BaseMetric] = [
        CategoryDetectionMetric(threshold=1.0),
        DateExtractionMetric(threshold=1.0),
        EventCountMetric(threshold=1.0),
    ]
    assert_test(test_case=test_case, metrics=metrics, run_async=False)
