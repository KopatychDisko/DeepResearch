"""Fetch company news and press-release signals from open web sources."""

from __future__ import annotations

from agents.configuration import Configuration
from agents.models import CompanyIdentity, RawFinding, SourceType
from agents.sources.common import fetch_source_findings


def fetch_news(identity: CompanyIdentity, settings: Configuration) -> list[RawFinding]:
    """Search company news in open web sources."""
    return fetch_source_findings(source_type=SourceType.NEWS, identity=identity, settings=settings)
