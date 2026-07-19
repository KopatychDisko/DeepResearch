from __future__ import annotations

from agents.configuration import Configuration
from agents.models import CompanyIdentity, RawFinding, SourceType
from agents.sources.common import fetch_source_findings


def fetch_hh(identity: CompanyIdentity, settings: Configuration) -> list[RawFinding]:
    return fetch_source_findings(source_type=SourceType.HH, identity=identity, settings=settings)
