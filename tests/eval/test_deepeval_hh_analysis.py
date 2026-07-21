from __future__ import annotations

import json

import pytest
from deepeval import assert_test
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from tests.eval_common import EvalQualityMetric
from tests.hh_eval_utils import (
    HhAnalysisGoldenCase,
    load_hh_analysis_golden_cases,
    no_llm_when_empty_score,
    run_hh_analysis,
    status_score,
    vacancy_cap_score,
)

pytestmark = pytest.mark.eval


class StatusMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "Status"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[HhAnalysisGoldenCase] = load_hh_analysis_golden_cases()
        selected_case: HhAnalysisGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        result = run_hh_analysis(case=selected_case)
        self.score = status_score(case=selected_case, result=result)
        self.success = self.score >= self.threshold
        return self.score


class VacancyCapMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "Vacancy Cap"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[HhAnalysisGoldenCase] = load_hh_analysis_golden_cases()
        selected_case: HhAnalysisGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        result = run_hh_analysis(case=selected_case)
        self.score = vacancy_cap_score(case=selected_case, result=result)
        self.success = self.score >= self.threshold
        return self.score


class NoLlmWhenEmptyMetric(EvalQualityMetric):
    @property
    def __name__(self) -> str:
        return "No LLM When Empty"

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        payload: dict[str, object] = json.loads(test_case.input)
        case_id: str = str(payload["case_id"])
        cases: list[HhAnalysisGoldenCase] = load_hh_analysis_golden_cases()
        selected_case: HhAnalysisGoldenCase = next(
            case for case in cases if case["id"] == case_id
        )
        result = run_hh_analysis(case=selected_case)
        self.score = no_llm_when_empty_score(case=selected_case, result=result)
        self.success = self.score >= self.threshold
        return self.score


@pytest.mark.parametrize(
    "case",
    load_hh_analysis_golden_cases(),
    ids=lambda case: case["id"],
)
def test_deepeval_hh_analysis(case: HhAnalysisGoldenCase) -> None:
    test_case = LLMTestCase(
        input=json.dumps({"case_id": case["id"]}),
        actual_output="hh_analysis_output",
        expected_output="hh_analysis_expected",
    )
    metrics: list[BaseMetric] = [
        StatusMetric(threshold=1.0),
        VacancyCapMetric(threshold=1.0),
        NoLlmWhenEmptyMetric(threshold=1.0),
    ]
    assert_test(test_case=test_case, metrics=metrics, run_async=False)
