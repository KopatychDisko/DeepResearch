"""Employer verdict and evidence models."""

from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from agents.models.enums import Confidence, EventCategory, VerdictColor


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
