"""LangGraph research-run state shape and JSON dump/load helpers."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, ToolMessage

from agents.models import (
    CanonicalTimeline,
    CompanyCandidate,
    CompanyEvent,
    CompanyIdentity,
    EmployerVerdict,
    HhVacancyAnalysis,
    RawFinding,
    RunRequest,
    SourceType,
)


def _replace_string(_left: str, right: str) -> str:
    return right


def _replace_optional_string(_left: str | None, right: str | None) -> str | None:
    return right


class ResearchRunState(TypedDict):
    """Checkpointed graph state for one employer due diligence research run."""

    run_id: str
    phase: Annotated[str, _replace_string]
    status: Annotated[str, _replace_string]
    error_message: Annotated[str | None, _replace_optional_string]
    request: dict[str, object]
    identity: dict[str, object]
    hh_vacancy_analysis: dict[str, object]
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
    """Serialize a RunRequest into JSON-compatible graph state."""
    return request.model_dump(mode="json")


def load_run_request(payload: dict[str, object]) -> RunRequest:
    """Deserialize a RunRequest from graph state."""
    return RunRequest.model_validate(payload)


def dump_company_identity(identity: CompanyIdentity) -> dict[str, object]:
    """Serialize a CompanyIdentity into JSON-compatible graph state."""
    return identity.model_dump(mode="json")


def load_company_identity(payload: dict[str, object]) -> CompanyIdentity:
    """Deserialize a CompanyIdentity from graph state."""
    return CompanyIdentity.model_validate(payload)


def dump_hh_vacancy_analysis(analysis: HhVacancyAnalysis) -> dict[str, object]:
    """Serialize an HhVacancyAnalysis into JSON-compatible graph state."""
    return analysis.model_dump(mode="json")


def load_hh_vacancy_analysis(payload: dict[str, object]) -> HhVacancyAnalysis:
    """Deserialize an HhVacancyAnalysis from graph state."""
    return HhVacancyAnalysis.model_validate(payload)


def is_hh_vacancy_analysis_pending(state: ResearchRunState) -> bool:
    """Return True when HH analysis has not yet been fetched for this run."""
    raw_analysis: object = state.get("hh_vacancy_analysis")
    if raw_analysis is None or raw_analysis == {}:
        return True
    if not isinstance(raw_analysis, dict):
        raise TypeError("hh_vacancy_analysis must be a dict in graph state")
    analysis = load_hh_vacancy_analysis(raw_analysis)
    return analysis.fetched_at == ""


def dump_raw_findings(findings: list[RawFinding]) -> list[dict[str, object]]:
    """Serialize raw findings into JSON-compatible graph state."""
    return [finding.model_dump(mode="json") for finding in findings]


def load_raw_findings(payload: list[dict[str, object]]) -> list[RawFinding]:
    """Deserialize raw findings from graph state."""
    return [RawFinding.model_validate(item) for item in payload]


def dump_company_events(events: list[CompanyEvent]) -> list[dict[str, object]]:
    """Serialize company events into JSON-compatible graph state."""
    return [event.model_dump(mode="json") for event in events]


def load_company_events(payload: list[dict[str, object]]) -> list[CompanyEvent]:
    """Deserialize company events from graph state."""
    return [CompanyEvent.model_validate(item) for item in payload]


def dump_canonical_timeline(timeline: CanonicalTimeline) -> dict[str, object]:
    """Serialize a CanonicalTimeline into JSON-compatible graph state."""
    return timeline.model_dump(mode="json")


def load_canonical_timeline(payload: dict[str, object]) -> CanonicalTimeline:
    """Deserialize a CanonicalTimeline from graph state."""
    return CanonicalTimeline.model_validate(payload)


def dump_employer_verdict(verdict: EmployerVerdict) -> dict[str, object]:
    """Serialize an EmployerVerdict into JSON-compatible graph state."""
    return verdict.model_dump(mode="json")


def load_employer_verdict(payload: dict[str, object]) -> EmployerVerdict:
    """Deserialize an EmployerVerdict from graph state."""
    return EmployerVerdict.model_validate(payload)


def dump_company_candidates(candidates: list[CompanyCandidate]) -> list[dict[str, object]]:
    """Serialize identity candidates into JSON-compatible graph state."""
    return [candidate.model_dump(mode="json") for candidate in candidates]


def load_company_candidates(payload: list[dict[str, object]]) -> list[CompanyCandidate]:
    """Deserialize identity candidates from graph state."""
    return [CompanyCandidate.model_validate(item) for item in payload]


def dump_completed_sources(sources: list[SourceType]) -> list[str]:
    """Serialize completed source types to their string values."""
    return [source.value for source in sources]


def load_completed_sources(payload: list[str]) -> list[SourceType]:
    """Deserialize completed source type strings into SourceType values."""
    return [SourceType(source_value) for source_value in payload]
