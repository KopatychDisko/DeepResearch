from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class SourceType(str, Enum):
    NEWS = "news"
    REVIEWS = "reviews"
    HH = "hh"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResponseLanguage(str, Enum):
    RU = "ru"
    EN = "en"


class RetrievalMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fetched_at: datetime
    source_label: str
    note: str


class CompanyIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query_name: str
    canonical_name: str
    normalized_name: str
    company_url: AnyHttpUrl | None = None
    profile_summary: str | None = None
    user_description: str | None = None


class CompanyCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    website_url: AnyHttpUrl | None = None
    confidence: Confidence


class StructuredCompanyCandidates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[CompanyCandidate]


class IdentityConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1)


class RawFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: SourceType
    source_url: AnyHttpUrl
    title: str
    snippet: str
    metadata: RetrievalMetadata


class EventCategory(str, Enum):
    FUNDING = "funding"
    LEADERSHIP = "leadership"
    LAYOFFS = "layoffs"
    SCANDAL = "scandal"
    PRODUCT = "product"
    REVIEW_SIGNAL = "review_signal"


class CompanyEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    date: str | None
    category: EventCategory
    description: str = Field(min_length=1)
    source_url: AnyHttpUrl
    confidence: Confidence


class CanonicalTimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    date: str | None
    category: EventCategory
    description: str = Field(min_length=1)
    source_urls: list[AnyHttpUrl] = Field(min_length=1)
    confidence: Confidence
    has_date_conflict: bool


class TimelineConflict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    category: EventCategory
    message: str = Field(min_length=1)
    source_urls: list[AnyHttpUrl] = Field(min_length=1)
    dates: list[str] = Field(min_length=2)


class CanonicalTimeline(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    events: list[CanonicalTimelineEvent]
    conflicts: list[TimelineConflict]


class VerdictColor(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class VerdictEvidenceLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_description: str = Field(min_length=1)
    category: EventCategory
    confidence: Confidence
    source_urls: list[AnyHttpUrl] = Field(min_length=1)
    date: str | None


class StructuredEmployerVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color: VerdictColor
    score: int = Field(ge=1, le=10)
    score_explanation: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    interesting_facts: list[str]


class EmployerVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    color: VerdictColor
    score: int = Field(ge=1, le=10)
    score_explanation: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    risks: list[str]
    red_flags: list[str]
    interesting_facts: list[str]
    evidence_links: list[VerdictEvidenceLink]


class RunPhase(str, Enum):
    PENDING = "pending"
    RESOLVE_IDENTITY = "resolve_identity"
    AWAITING_IDENTITY = "awaiting_identity"
    SUPERVISOR = "supervisor"
    STRUCTURE_EVENTS = "structure_events"
    MERGE_TIMELINE = "merge_timeline"
    GENERATE_VERDICT = "generate_verdict"
    COMPLETED = "completed"


class RunLifecycleStatus(str, Enum):
    RUNNING = "running"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    company_name: str = Field(min_length=2, max_length=200)
    company_url: AnyHttpUrl | None = None
    company_description: str | None = None
    response_language: ResponseLanguage = ResponseLanguage.RU

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, company_name: str) -> str:
        stripped_name: str = company_name.strip()
        if len(stripped_name) < 2:
            raise ValueError("company_name must contain at least 2 non-space characters")
        return stripped_name

    @field_validator("company_description")
    @classmethod
    def validate_company_description(cls, company_description: str | None) -> str | None:
        if company_description is None:
            return None
        stripped_description: str = company_description.strip()
        if not stripped_description:
            return None
        if len(stripped_description) > 500:
            raise ValueError("company_description must be at most 500 characters")
        return stripped_description


class RunResponse(BaseModel):
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
    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: CompanyIdentity
    findings: list[RawFinding]
    events: list[CompanyEvent]
    timeline: CanonicalTimeline
    verdict: EmployerVerdict


class RunStatusResponse(BaseModel):
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
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    created_at: datetime
    status: RunLifecycleStatus
    phase: RunPhase
    message: str


class StructuredCompanyEvents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[CompanyEvent]


def utc_now() -> datetime:
    return datetime.now(UTC)
