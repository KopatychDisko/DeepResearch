from __future__ import annotations

import json

import pytest
from deepeval import assert_test
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from tests.merge_eval_utils import (
    conflict_accuracy_score,
    date_fact_accuracy_score,
    dedup_precision_score,
    dedup_recall_score,
    load_merge_golden_cases,
    merge_case,
)

pytestmark = pytest.mark.eval


class MergeQualityMetric(BaseMetric):
    def is_successful(self) -> bool:
        if self.success is None:
            return False
        return self.success


class DedupRecallMetric(MergeQualityMetric):
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.async_mode = False

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases = load_merge_golden_cases()
        selected_case = next(case for case in cases if case["id"] == case_id)
        timeline = merge_case(case=selected_case)
        self.score = dedup_recall_score(case=selected_case, timeline=timeline)
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case=test_case, *args, **kwargs)


class DedupPrecisionMetric(MergeQualityMetric):
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.async_mode = False

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases = load_merge_golden_cases()
        selected_case = next(case for case in cases if case["id"] == case_id)
        timeline = merge_case(case=selected_case)
        self.score = dedup_precision_score(case=selected_case, timeline=timeline)
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case=test_case, *args, **kwargs)


class DateFactAccuracyMetric(MergeQualityMetric):
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.async_mode = False

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases = load_merge_golden_cases()
        selected_case = next(case for case in cases if case["id"] == case_id)
        timeline = merge_case(case=selected_case)
        self.score = date_fact_accuracy_score(case=selected_case, timeline=timeline)
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case=test_case, *args, **kwargs)


class ConflictDetectionMetric(MergeQualityMetric):
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.async_mode = False

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases = load_merge_golden_cases()
        selected_case = next(case for case in cases if case["id"] == case_id)
        timeline = merge_case(case=selected_case)
        self.score = conflict_accuracy_score(case=selected_case, timeline=timeline)
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case=test_case, *args, **kwargs)


@pytest.mark.parametrize("case", load_merge_golden_cases(), ids=lambda case: case["id"])
def test_deepeval_merge_quality_baseline(case) -> None:
    test_case = LLMTestCase(
        input=json.dumps({"case_id": case["id"]}),
        actual_output="merge_pipeline_output",
        expected_output="merge_pipeline_expected",
    )
    metrics: list[BaseMetric] = [
        DedupRecallMetric(threshold=0.99),
        DedupPrecisionMetric(threshold=1.0),
        DateFactAccuracyMetric(threshold=1.0),
        ConflictDetectionMetric(threshold=1.0),
    ]
    assert_test(test_case=test_case, metrics=metrics)
