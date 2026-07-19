from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, ToolMessage

from agents.models import (
    CanonicalTimeline,
    CompanyCandidate,
    CompanyEvent,
    CompanyIdentity,
    EmployerVerdict,
    RawFinding,
    RunRequest,
    SourceType,
)


def _replace_string(_left: str, right: str) -> str:
    return right


def _replace_optional_string(_left: str | None, right: str | None) -> str | None:
    return right


class ResearchRunState(TypedDict):
    run_id: str
    phase: Annotated[str, _replace_string]
    status: Annotated[str, _replace_string]
    error_message: Annotated[str | None, _replace_optional_string]
    request: dict[str, object]
    identity: dict[str, object]
    findings: list[dict[str, object]]
    events: list[dict[str, object]]
    timeline: dict[str, object]
    verdict: dict[str, object]
    identity_candidates: list[dict[str, object]]
    completed_sources: list[str]
    conversation_history: list[AIMessage | ToolMessage]
    iteration_count: int
    finished: bool
    budget_deadline_unix: float | None
    estimated_tokens_used: int
    budget_stop_reason: str | None


def dump_run_request(request: RunRequest) -> dict[str, object]:
    return request.model_dump(mode="json")


def load_run_request(payload: dict[str, object]) -> RunRequest:
    return RunRequest.model_validate(payload)


def dump_company_identity(identity: CompanyIdentity) -> dict[str, object]:
    return identity.model_dump(mode="json")


def load_company_identity(payload: dict[str, object]) -> CompanyIdentity:
    return CompanyIdentity.model_validate(payload)


def dump_raw_findings(findings: list[RawFinding]) -> list[dict[str, object]]:
    return [finding.model_dump(mode="json") for finding in findings]


def load_raw_findings(payload: list[dict[str, object]]) -> list[RawFinding]:
    return [RawFinding.model_validate(item) for item in payload]


def dump_company_events(events: list[CompanyEvent]) -> list[dict[str, object]]:
    return [event.model_dump(mode="json") for event in events]


def load_company_events(payload: list[dict[str, object]]) -> list[CompanyEvent]:
    return [CompanyEvent.model_validate(item) for item in payload]


def dump_canonical_timeline(timeline: CanonicalTimeline) -> dict[str, object]:
    return timeline.model_dump(mode="json")


def load_canonical_timeline(payload: dict[str, object]) -> CanonicalTimeline:
    return CanonicalTimeline.model_validate(payload)


def dump_employer_verdict(verdict: EmployerVerdict) -> dict[str, object]:
    return verdict.model_dump(mode="json")


def load_employer_verdict(payload: dict[str, object]) -> EmployerVerdict:
    return EmployerVerdict.model_validate(payload)


def dump_company_candidates(candidates: list[CompanyCandidate]) -> list[dict[str, object]]:
    return [candidate.model_dump(mode="json") for candidate in candidates]


def load_company_candidates(payload: list[dict[str, object]]) -> list[CompanyCandidate]:
    return [CompanyCandidate.model_validate(item) for item in payload]


def dump_completed_sources(sources: list[SourceType]) -> list[str]:
    return [source.value for source in sources]


def load_completed_sources(payload: list[str]) -> list[SourceType]:
    return [SourceType(source_value) for source_value in payload]
