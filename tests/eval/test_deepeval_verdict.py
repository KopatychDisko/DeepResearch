from __future__ import annotations

import json

import pytest
from deepeval import assert_test
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from tests.eval_common import EvalQualityMetric
from tests.verdict_eval_utils import (
    VerdictGoldenCase,
    build_timeline,
    load_verdict_golden_cases,
    score_evidence_links,
    score_red_flags,
    score_risks,
)

pytestmark = pytest.mark.eval


class RedFlagMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "Red Flag"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[VerdictGoldenCase] = load_verdict_golden_cases()
        selected_case: VerdictGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        timeline = build_timeline(case=selected_case)
        self.score = score_red_flags(case=selected_case, timeline=timeline)
        self.success = self.score >= self.threshold
        return self.score


class RiskMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "Risk"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[VerdictGoldenCase] = load_verdict_golden_cases()
        selected_case: VerdictGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        timeline = build_timeline(case=selected_case)
        self.score = score_risks(case=selected_case, timeline=timeline)
        self.success = self.score >= self.threshold
        return self.score


class EvidenceLinkMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "Evidence Link"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[VerdictGoldenCase] = load_verdict_golden_cases()
        selected_case: VerdictGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        timeline = build_timeline(case=selected_case)
        self.score = score_evidence_links(case=selected_case, timeline=timeline)
        self.success = self.score >= self.threshold
        return self.score


@pytest.mark.parametrize(
    "case",
    load_verdict_golden_cases(),
    ids=lambda case: case["id"],
)
def test_deepeval_verdict(case: VerdictGoldenCase) -> None:
    test_case = LLMTestCase(
        input=json.dumps({"case_id": case["id"]}),
        actual_output="verdict_signals_output",
        expected_output="verdict_signals_expected",
    )
    metrics: list[BaseMetric] = [
        RedFlagMetric(threshold=1.0),
        RiskMetric(threshold=1.0),
        EvidenceLinkMetric(threshold=1.0),
    ]
    assert_test(test_case=test_case, metrics=metrics, run_async=False)
