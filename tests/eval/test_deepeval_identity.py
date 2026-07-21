from __future__ import annotations

import json

import pytest
from deepeval import assert_test
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from tests.eval_common import EvalQualityMetric
from tests.identity_eval_utils import (
    IdentityGoldenCase,
    auto_confirm_score,
    host_normalize_score,
    load_identity_golden_cases,
    run_auto_confirm,
)

pytestmark = pytest.mark.eval


class AutoConfirmMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "Auto Confirm"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[IdentityGoldenCase] = load_identity_golden_cases()
        selected_case: IdentityGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        selected = run_auto_confirm(case=selected_case)
        self.score = auto_confirm_score(case=selected_case, selected=selected)
        self.success = self.score >= self.threshold
        return self.score


class HostNormalizeMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "Host Normalize"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[IdentityGoldenCase] = load_identity_golden_cases()
        selected_case: IdentityGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        self.score = host_normalize_score(case=selected_case)
        self.success = self.score >= self.threshold
        return self.score


@pytest.mark.parametrize(
    "case",
    load_identity_golden_cases(),
    ids=lambda case: case["id"],
)
def test_deepeval_identity(case: IdentityGoldenCase) -> None:
    test_case = LLMTestCase(
        input=json.dumps({"case_id": case["id"]}),
        actual_output="identity_resolution_output",
        expected_output="identity_resolution_expected",
    )
    metrics: list[BaseMetric] = [
        AutoConfirmMetric(threshold=1.0),
        HostNormalizeMetric(threshold=1.0),
    ]
    assert_test(test_case=test_case, metrics=metrics, run_async=False)
