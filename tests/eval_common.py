from __future__ import annotations

import json
from pathlib import Path

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class EvalQualityMetric(BaseMetric):
    """Sync deterministic metric base for DeepEval quality scorers."""

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.async_mode = False
        self.score: float = 0.0
        self.success: bool | None = None

    def is_successful(self) -> bool:
        if self.success is None:
            return False
        return self.success

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case=test_case, *args, **kwargs)


def load_golden_dataset(dataset_name: str) -> list[dict[str, object]]:
    dataset_path: Path = (
        Path(__file__).resolve().parents[1] / "eval" / "datasets" / f"{dataset_name}.json"
    )
    raw_cases: object = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(raw_cases, list):
        raise TypeError(f"{dataset_name}.json must contain a list of cases")
    typed_cases: list[dict[str, object]] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise TypeError(f"Each case in {dataset_name}.json must be an object")
        typed_cases.append(raw_case)
    return typed_cases
