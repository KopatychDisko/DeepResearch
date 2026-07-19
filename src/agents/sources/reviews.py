"""Fetch employee reviews and workplace reputation signals."""

from __future__ import annotations

from agents.configuration import Configuration
from agents.models import CompanyIdentity, RawFinding, SourceType
from agents.sources.common import fetch_source_findings


def fetch_reviews(identity: CompanyIdentity, settings: Configuration) -> list[RawFinding]:
    """Search employee reviews and reputation signals."""
    return fetch_source_findings(
        source_type=SourceType.REVIEWS, identity=identity, settings=settings
    )
