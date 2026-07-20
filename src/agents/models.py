"""Domain and API models for employer due diligence research runs."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class SourceType(str, Enum):
    """Research source channel used by supervisor search tools."""

    NEWS = "news"
    REVIEWS = "reviews"
    HH = "hh"


class Confidence(str, Enum):
    """Evidence confidence level for findings and events."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResponseLanguage(str, Enum):
    """Language for user-facing research output."""

    RU = "ru"
    EN = "en"


class RetrievalMetadata(BaseModel):
    """Provenance metadata attached to a retrieved raw finding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fetched_at: datetime
    source_label: str
    note: str


class CompanyIdentity(BaseModel):
    """Resolved company identity used throughout the research graph."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query_name: str
    canonical_name: str
    normalized_name: str
    company_url: AnyHttpUrl | None = None
    profile_summary: str | None = None
    user_description: str | None = None


class CompanyCandidate(BaseModel):
    """Ambiguous identity match offered for user confirmation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    website_url: AnyHttpUrl | None = None
    confidence: Confidence


class StructuredCompanyCandidates(BaseModel):
    """Structured LLM output wrapper for identity candidate lists."""

    model_config = ConfigDict(extra="forbid")

    candidates: list[CompanyCandidate]


class IdentityConfirmationRequest(BaseModel):
    """User selection of one identity candidate to continue the run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str = Field(min_length=1)


class RawFinding(BaseModel):
    """Source-grounded snippet collected before event structuring."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: SourceType
    source_url: AnyHttpUrl
    title: str
    snippet: str
    metadata: RetrievalMetadata


class EventCategory(str, Enum):
    """Canonical event category for timeline items."""

    FUNDING = "funding"
    LEADERSHIP = "leadership"
    LAYOFFS = "layoffs"
    SCANDAL = "scandal"
    PRODUCT = "product"
    REVIEW_SIGNAL = "review_signal"


class CompanyEvent(BaseModel):
    """Structured event extracted from one or more raw findings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    date: str | None
    category: EventCategory
    description: str = Field(min_length=1)
    source_url: AnyHttpUrl
    confidence: Confidence


class CanonicalTimelineEvent(BaseModel):
    """Deduplicated timeline event with merged source URLs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    date: str | None
    category: EventCategory
    description: str = Field(min_length=1)
    source_urls: list[AnyHttpUrl] = Field(min_length=1)
    confidence: Confidence
    has_date_conflict: bool


class TimelineConflict(BaseModel):
    """Recorded disagreement between sources about the same event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: EventCategory
    message: str = Field(min_length=1)
    source_urls: list[AnyHttpUrl] = Field(min_length=1)
    dates: list[str] = Field(min_length=2)


class CanonicalTimeline(BaseModel):
    """Merged timeline plus conflicts produced by the merge step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    events: list[CanonicalTimelineEvent]
    conflicts: list[TimelineConflict]


class VerdictColor(str, Enum):
    """High-level employer risk signal for the verdict card."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class VerdictEvidenceLink(BaseModel):
    """Timeline evidence cited by the employer verdict."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_description: str = Field(min_length=1)
    category: EventCategory
    confidence: Confidence
    source_urls: list[AnyHttpUrl] = Field(min_length=1)
    date: str | None


class StructuredEmployerVerdict(BaseModel):
    """Structured LLM output for score and summary before enrichment."""

    model_config = ConfigDict(extra="forbid")

    color: VerdictColor
    score: int = Field(ge=1, le=10)
    score_explanation: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    interesting_facts: list[str]


class EmployerVerdict(BaseModel):
    """Final employer verdict with risks, red flags, and evidence links."""

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
    """Pipeline phase reported for run progress and status APIs."""

    PENDING = "pending"
    RESOLVE_IDENTITY = "resolve_identity"
    AWAITING_IDENTITY = "awaiting_identity"
    ANALYZE_HH_VACANCIES = "analyze_hh_vacancies"
    SUPERVISOR = "supervisor"
    STRUCTURE_EVENTS = "structure_events"
    MERGE_TIMELINE = "merge_timeline"
    GENERATE_VERDICT = "generate_verdict"
    COMPLETED = "completed"


class RunLifecycleStatus(str, Enum):
    """Lifecycle status of a research run for API clients."""

    RUNNING = "running"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


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


class StructuredCompanyEvents(BaseModel):
    """Structured LLM output wrapper for extracted company events."""

    model_config = ConfigDict(extra="forbid")

    events: list[CompanyEvent]


class ToolObservationStatus(str, Enum):
    """Outcome status carried in harness ToolObservation JSON messages."""

    OK = "ok"
    ERROR = "error"
    DENIED = "denied"


class HhVacancyStatus(str, Enum):
    """Outcome status for hh.ru vacancy analysis blocks."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    ERROR = "error"


class HhSalaryRange(BaseModel):
    """Salary range parsed from hh.ru vacancy list or detail payloads."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    from_amount: int | None
    to_amount: int | None
    currency: str | None
    gross: bool | None


class HhVacancyItem(BaseModel):
    """Single active vacancy row sourced from api.hh.ru."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    vacancy_id: str
    title: str
    url: AnyHttpUrl
    area_name: str | None
    salary: HhSalaryRange | None
    employment_type: str | None
    schedule: str | None
    experience: str | None
    working_conditions: list[str]
    published_at: str | None


class HhEmployerRating(BaseModel):
    """Employer rating and trust signals when present in hh.ru profile data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    available: bool
    average_score: float | None
    reviews_count: int | None
    recommendation_percent: float | None
    trusted: bool | None
    accredited_it_employer: bool | None
    source_url: AnyHttpUrl | None


class HhVacancySummary(BaseModel):
    """Employer profile summary attached to vacancy analysis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    employer_id: str
    name: str
    profile_url: AnyHttpUrl
    site_url: AnyHttpUrl | None
    open_vacancies_count: int | None
    rating: HhEmployerRating


class StructuredHhVacancyAssessment(BaseModel):
    """Structured LLM output for hh.ru vacancy salary and conditions summaries."""

    model_config = ConfigDict(extra="forbid")

    salary_summary: str = Field(min_length=1)
    conditions_summary: str = Field(min_length=1)
    employer_rating_text: str = Field(min_length=1)


class HhVacancyAnalysis(BaseModel):
    """Structured hh.ru vacancy assessment block stored separately from timeline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: HhVacancyStatus
    message: str
    search_query: str
    employer: HhVacancySummary | None
    vacancies: list[HhVacancyItem]
    salary_summary: str
    conditions_summary: str
    fetched_at: str


class ToolObservation(BaseModel):
    """Structured tool outcome the harness writes into ToolMessage content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ToolObservationStatus
    tool: str
    summary: str
    counts: dict[str, int] | None = None
    source: str | None = None
    error_code: str | None = None
    error_message: str | None = None


def utc_now() -> datetime:
    """Return the current UTC timestamp for run and retrieval metadata."""
    return datetime.now(UTC)
