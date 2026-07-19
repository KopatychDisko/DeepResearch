from __future__ import annotations

from agents.configuration import Configuration
from agents.models import CompanyIdentity, RawFinding, SourceType
from agents.sources.common import fetch_source_findings


def fetch_reviews(identity: CompanyIdentity, settings: Configuration) -> list[RawFinding]:
    return fetch_source_findings(
        source_type=SourceType.REVIEWS, identity=identity, settings=settings
    )
