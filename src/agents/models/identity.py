"""Company identity resolution models."""

from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from agents.models.enums import Confidence


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
