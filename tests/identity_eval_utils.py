from __future__ import annotations

from typing import NotRequired, TypedDict

from pydantic import AnyHttpUrl

from agents.identity.resolution import _pick_auto_confirmed_candidate, normalize_host
from agents.models import CompanyCandidate, Confidence
from tests.eval_common import load_golden_dataset


class IdentityGoldenCandidate(TypedDict):
    candidate_id: str
    name: str
    description: str
    website_url: str | None
    confidence: str


class IdentityGoldenCase(TypedDict):
    id: str
    candidates: list[IdentityGoldenCandidate]
    requested_company_url: str | None
    expected_selected_name: str | None
    expected_auto_confirm: bool
    input_url: NotRequired[str]
    expected_normalized_host: NotRequired[str]


def load_identity_golden_cases() -> list[IdentityGoldenCase]:
    raw_cases: list[dict[str, object]] = load_golden_dataset("identity_golden")
    typed_cases: list[IdentityGoldenCase] = []
    for raw_case in raw_cases:
        if "id" not in raw_case or not isinstance(raw_case["id"], str):
            raise TypeError("Each identity golden case must have a string id")
        if "candidates" not in raw_case or not isinstance(raw_case["candidates"], list):
            raise TypeError(f"Case {raw_case['id']} must have a candidates list")
        if "expected_auto_confirm" not in raw_case or not isinstance(
            raw_case["expected_auto_confirm"], bool
        ):
            raise TypeError(f"Case {raw_case['id']} must have a boolean expected_auto_confirm")
        for candidate in raw_case["candidates"]:
            if not isinstance(candidate, dict):
                raise TypeError(f"Case {raw_case['id']} candidates must contain objects")
            if "candidate_id" not in candidate or not isinstance(candidate["candidate_id"], str):
                raise TypeError(f"Case {raw_case['id']} candidates must have candidate_id")
            if "name" not in candidate or not isinstance(candidate["name"], str):
                raise TypeError(f"Case {raw_case['id']} candidates must have name")
            if "description" not in candidate or not isinstance(candidate["description"], str):
                raise TypeError(f"Case {raw_case['id']} candidates must have description")
            if "confidence" not in candidate or not isinstance(candidate["confidence"], str):
                raise TypeError(f"Case {raw_case['id']} candidates must have confidence")
        typed_cases.append(raw_case)  # type: ignore[arg-type]
    return typed_cases


def build_candidates(case: IdentityGoldenCase) -> list[CompanyCandidate]:
    candidates: list[CompanyCandidate] = []
    for candidate_data in case["candidates"]:
        website_url: AnyHttpUrl | None = None
        if candidate_data["website_url"] is not None:
            website_url = AnyHttpUrl(candidate_data["website_url"])
        candidates.append(
            CompanyCandidate(
                candidate_id=candidate_data["candidate_id"],
                name=candidate_data["name"],
                description=candidate_data["description"],
                website_url=website_url,
                confidence=Confidence(candidate_data["confidence"]),
            )
        )
    return candidates


def run_auto_confirm(case: IdentityGoldenCase) -> CompanyCandidate | None:
    candidates: list[CompanyCandidate] = build_candidates(case=case)
    requested_company_url: AnyHttpUrl | None = None
    if case["requested_company_url"] is not None:
        requested_company_url = AnyHttpUrl(case["requested_company_url"])
    return _pick_auto_confirmed_candidate(
        candidates=candidates,
        requested_company_url=requested_company_url,
    )


def auto_confirm_score(
    case: IdentityGoldenCase,
    selected: CompanyCandidate | None,
) -> float:
    expected_auto_confirm: bool = case["expected_auto_confirm"]
    if (selected is None) != (not expected_auto_confirm):
        return 0.0
    expected_selected_name: str | None = case["expected_selected_name"]
    actual_selected_name: str | None = selected.name if selected is not None else None
    if actual_selected_name != expected_selected_name:
        return 0.0
    return 1.0


def host_normalize_score(case: IdentityGoldenCase) -> float:
    if "input_url" not in case:
        return 1.0
    if "expected_normalized_host" not in case:
        raise ValueError(f"Case {case['id']} has input_url but no expected_normalized_host")
    input_url: str = case["input_url"]
    expected_normalized_host: str = case["expected_normalized_host"]
    if normalize_host(input_url) != expected_normalized_host:
        return 0.0
    return 1.0
