"""HTTP request and response models for research run APIs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from agents.models.enums import ResponseLanguage, RunLifecycleStatus, RunPhase, SourceType
from agents.models.hh import HhVacancyAnalysis
from agents.models.identity import CompanyCandidate, CompanyIdentity
from agents.models.research import CanonicalTimeline, CompanyEvent, RawFinding
from agents.models.verdict import EmployerVerdict


class HhEmployerSearchRequest(BaseModel):
    """Manual hh.ru employer search retry query for a completed run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    employer_query: str = Field(min_length=1)


class RunRequest(BaseModel):
    """Inbound request to start an employer due diligence research run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    company_name: str = Field(min_length=2, max_length=200)
    company_url: AnyHttpUrl | None = None
    company_description: str | None = None
    response_language: ResponseLanguage = ResponseLanguage.RU

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, company_name: str) -> str:
        """Strip and enforce a minimum non-space company name length."""
        stripped_name: str = company_name.strip()
        if len(stripped_name) < 2:
            raise ValueError("company_name must contain at least 2 non-space characters")
        return stripped_name

    @field_validator("company_description")
    @classmethod
    def validate_company_description(cls, company_description: str | None) -> str | None:
        """Normalize blank descriptions to None and cap length at 500 characters."""
        if company_description is None:
            return None
        stripped_description: str = company_description.strip()
        if not stripped_description:
            return None
        if len(stripped_description) > 500:
            raise ValueError("company_description must be at most 500 characters")
        return stripped_description


class RunResponse(BaseModel):
    """Completed research payload returned by synchronous run APIs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    created_at: datetime
    identity: CompanyIdentity
    findings: list[RawFinding]
    events: list[CompanyEvent]
    timeline: CanonicalTimeline
    verdict: EmployerVerdict
    note: str


class ResearchRunResult(BaseModel):
    """Core research artifacts attached to a finished run status."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: CompanyIdentity
    findings: list[RawFinding]
    events: list[CompanyEvent]
    timeline: CanonicalTimeline
    verdict: EmployerVerdict
    hh_vacancy_analysis: HhVacancyAnalysis


class RunStatusResponse(BaseModel):
    """Polling response for run progress, identity waits, and final result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    created_at: datetime
    status: RunLifecycleStatus
    phase: RunPhase
    company_name: str
    completed_sources: list[SourceType]
    findings_count: int
    events_count: int
    iteration_count: int
    error_message: str | None
    identity_candidates: list[CompanyCandidate]
    result: ResearchRunResult | None


class RunStartResponse(BaseModel):
    """Acknowledgement returned when a research run is accepted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    created_at: datetime
    status: RunLifecycleStatus
    phase: RunPhase
    message: str
