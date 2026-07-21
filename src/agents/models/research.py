"""Raw findings, structured events, and canonical timeline models."""

from __future__ import annotations

from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from agents.models.enums import Confidence, EventCategory, SourceType


class RetrievalMetadata(BaseModel):
    """Provenance metadata attached to a retrieved raw finding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fetched_at: datetime
    source_label: str
    note: str


class RawFinding(BaseModel):
    """Source-grounded snippet collected before event structuring."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_type: SourceType
    source_url: AnyHttpUrl
    title: str
    snippet: str
    metadata: RetrievalMetadata


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


class StructuredCompanyEvents(BaseModel):
    """Structured LLM output wrapper for extracted company events."""

    model_config = ConfigDict(extra="forbid")

    events: list[CompanyEvent]
