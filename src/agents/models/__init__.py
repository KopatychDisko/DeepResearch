"""Domain and API models for employer due diligence research runs."""

from __future__ import annotations

from agents.models.common import utc_now
from agents.models.enums import (
    Confidence,
    EventCategory,
    HhVacancyStatus,
    ResponseLanguage,
    RunLifecycleStatus,
    RunPhase,
    SourceType,
    ToolObservationStatus,
    VerdictColor,
)
from agents.models.harness import ToolObservation
from agents.models.hh import (
    HhEmployerRating,
    HhSalaryRange,
    HhVacancyAnalysis,
    HhVacancyItem,
    HhVacancySummary,
    StructuredHhEmployerSearchReformulation,
    StructuredHhVacancyAssessment,
)
from agents.models.identity import (
    CompanyCandidate,
    CompanyIdentity,
    IdentityConfirmationRequest,
    StructuredCompanyCandidates,
)
from agents.models.research import (
    CanonicalTimeline,
    CanonicalTimelineEvent,
    CompanyEvent,
    RawFinding,
    RetrievalMetadata,
    StructuredCompanyEvents,
    TimelineConflict,
)
from agents.models.run import (
    HhEmployerSearchRequest,
    ResearchRunResult,
    RunRequest,
    RunResponse,
    RunStartResponse,
    RunStatusResponse,
)
from agents.models.verdict import (
    EmployerVerdict,
    StructuredEmployerVerdict,
    VerdictEvidenceLink,
)

__all__ = [
    "CanonicalTimeline",
    "CanonicalTimelineEvent",
    "CompanyCandidate",
    "CompanyEvent",
    "CompanyIdentity",
    "Confidence",
    "EmployerVerdict",
    "EventCategory",
    "HhEmployerRating",
    "HhEmployerSearchRequest",
    "HhSalaryRange",
    "HhVacancyAnalysis",
    "HhVacancyItem",
    "HhVacancyStatus",
    "HhVacancySummary",
    "IdentityConfirmationRequest",
    "RawFinding",
    "ResearchRunResult",
    "ResponseLanguage",
    "RetrievalMetadata",
    "RunLifecycleStatus",
    "RunPhase",
    "RunRequest",
    "RunResponse",
    "RunStartResponse",
    "RunStatusResponse",
    "SourceType",
    "StructuredCompanyCandidates",
    "StructuredCompanyEvents",
    "StructuredEmployerVerdict",
    "StructuredHhEmployerSearchReformulation",
    "StructuredHhVacancyAssessment",
    "TimelineConflict",
    "ToolObservation",
    "ToolObservationStatus",
    "VerdictColor",
    "VerdictEvidenceLink",
    "utc_now",
]
