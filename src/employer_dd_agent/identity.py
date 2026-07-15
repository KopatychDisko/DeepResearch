from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from langchain_core.runnables import RunnableConfig
from pydantic import AnyHttpUrl

from employer_dd_agent.configuration import Configuration
from employer_dd_agent.models import (
    CompanyCandidate,
    CompanyIdentity,
    Confidence,
    ResponseLanguage,
    StructuredCompanyCandidates,
)
from employer_dd_agent.prompts import IDENTITY_RESOLUTION_PROMPT
from employer_dd_agent.language import (
    identity_ambiguous_message,
    identity_not_found_message,
    identity_unconfirmed_message,
    optional_description_placeholder,
    optional_url_placeholder,
    response_language_instruction,
)
from employer_dd_agent.sources import search_web
from employer_dd_agent.structured_output import invoke_structured_output


class IdentityResolutionStatus(str, Enum):
    CONFIRMED = "confirmed"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class IdentityResolutionResult:
    status: IdentityResolutionStatus
    candidates: list[CompanyCandidate]
    identity: CompanyIdentity | None
    message: str | None


def normalize_company_name(company_name: str) -> str:
    normalized: str = re.sub(r"\s+", " ", company_name.strip().lower())
    if not normalized:
        raise ValueError("company_name normalization produced an empty value")
    return normalized


def normalize_host(url_value: str) -> str:
    parsed = urlparse(url_value.strip())
    host: str = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _candidate_id(name: str, website_url: str | None) -> str:
    seed: str = f"{normalize_company_name(name)}|{website_url or ''}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def _assign_candidate_ids(candidates: list[CompanyCandidate]) -> list[CompanyCandidate]:
    assigned: list[CompanyCandidate] = []
    for candidate in candidates:
        assigned.append(
            CompanyCandidate(
                candidate_id=_candidate_id(
                    name=candidate.name,
                    website_url=str(candidate.website_url) if candidate.website_url is not None else None,
                ),
                name=candidate.name,
                description=candidate.description,
                website_url=candidate.website_url,
                confidence=candidate.confidence,
            )
        )
    return assigned


def candidate_to_identity(
    candidate: CompanyCandidate,
    query_name: str,
    requested_company_url: AnyHttpUrl | None,
    user_description: str | None,
) -> CompanyIdentity:
    website_url: AnyHttpUrl | None = candidate.website_url
    if website_url is None and requested_company_url is not None:
        website_url = requested_company_url
    return CompanyIdentity(
        query_name=query_name,
        canonical_name=candidate.name,
        normalized_name=normalize_company_name(candidate.name),
        company_url=website_url,
        profile_summary=candidate.description,
        user_description=user_description,
    )


def _search_results_text(results: list[dict[str, object]]) -> str:
    serialized: list[dict[str, str]] = []
    for index, item in enumerate(results):
        url_value = item.get("url")
        title_value = item.get("title")
        content_value = item.get("content")
        serialized.append(
            {
                "index": str(index),
                "url": url_value if isinstance(url_value, str) else "",
                "title": title_value if isinstance(title_value, str) else "",
                "snippet": content_value if isinstance(content_value, str) else "",
            }
        )
    return json.dumps(serialized, ensure_ascii=False, indent=2)


def _confidence_rank(confidence: Confidence) -> int:
    if confidence == Confidence.HIGH:
        return 3
    if confidence == Confidence.MEDIUM:
        return 2
    return 1


def _host_matches(candidate: CompanyCandidate, requested_host: str) -> bool:
    if candidate.website_url is None:
        return False
    return normalize_host(str(candidate.website_url)) == requested_host


def _pick_auto_confirmed_candidate(
    candidates: list[CompanyCandidate],
    requested_company_url: AnyHttpUrl | None,
) -> CompanyCandidate | None:
    if not candidates:
        return None

    if requested_company_url is not None:
        requested_host: str = normalize_host(str(requested_company_url))
        host_matches: list[CompanyCandidate] = [
            candidate for candidate in candidates if _host_matches(candidate, requested_host)
        ]
        if len(host_matches) == 1:
            return host_matches[0]
        if len(host_matches) > 1:
            return None

    ranked_candidates: list[CompanyCandidate] = sorted(
        candidates,
        key=lambda candidate: _confidence_rank(candidate.confidence),
        reverse=True,
    )
    high_confidence: list[CompanyCandidate] = [
        candidate
        for candidate in ranked_candidates
        if candidate.confidence in {Confidence.HIGH, Confidence.MEDIUM}
    ]
    if len(high_confidence) == 1:
        return high_confidence[0]
    if len(candidates) == 1 and candidates[0].confidence != Confidence.LOW:
        return candidates[0]
    return None


def _build_identity_search_query(
    company_name: str,
    company_url: AnyHttpUrl | None,
    company_description: str | None,
) -> str:
    description_part: str = ""
    if company_description is not None:
        description_part = f" {company_description}"
    if company_url is not None:
        host: str = normalize_host(str(company_url))
        return f'"{company_name}"{description_part} site:{host} company employer Russia'
    return f'"{company_name}"{description_part} company employer official website Russia'


def resolve_company_identity_from_web(
    company_name: str,
    company_url: AnyHttpUrl | None,
    company_description: str | None,
    response_language: ResponseLanguage,
    config: RunnableConfig,
    settings: Configuration,
) -> IdentityResolutionResult:
    query: str = _build_identity_search_query(
        company_name=company_name,
        company_url=company_url,
        company_description=company_description,
    )
    search_results: list[dict[str, object]] = search_web(
        query=query,
        max_results=settings.tavily_max_results,
    )
    if not search_results:
        return IdentityResolutionResult(
            status=IdentityResolutionStatus.NOT_FOUND,
            candidates=[],
            identity=None,
            message=identity_not_found_message(
                company_name=company_name,
                language=response_language,
            ),
        )

    parsed_output = invoke_structured_output(
        config=config,
        model_class=StructuredCompanyCandidates,
        prompt=IDENTITY_RESOLUTION_PROMPT.format(
            company_name=company_name,
            company_url=(
                str(company_url)
                if company_url is not None
                else optional_url_placeholder(language=response_language)
            ),
            company_description=(
                company_description
                if company_description is not None
                else optional_description_placeholder(language=response_language)
            ),
            search_results_text=_search_results_text(search_results),
            response_language_instruction=response_language_instruction(
                language=response_language
            ),
        ),
    )
    candidates: list[CompanyCandidate] = _assign_candidate_ids(parsed_output.candidates)
    credible_candidates: list[CompanyCandidate] = [
        candidate for candidate in candidates if candidate.confidence != Confidence.LOW
    ]

    if not credible_candidates:
        return IdentityResolutionResult(
            status=IdentityResolutionStatus.NOT_FOUND,
            candidates=[],
            identity=None,
            message=identity_unconfirmed_message(
                company_name=company_name,
                language=response_language,
            ),
        )

    auto_candidate: CompanyCandidate | None = _pick_auto_confirmed_candidate(
        candidates=credible_candidates,
        requested_company_url=company_url,
    )
    if auto_candidate is not None:
        return IdentityResolutionResult(
            status=IdentityResolutionStatus.CONFIRMED,
            candidates=credible_candidates,
            identity=candidate_to_identity(
                candidate=auto_candidate,
                query_name=company_name,
                requested_company_url=company_url,
                user_description=company_description,
            ),
            message=None,
        )

    if len(credible_candidates) == 1:
        single_candidate: CompanyCandidate = credible_candidates[0]
        return IdentityResolutionResult(
            status=IdentityResolutionStatus.CONFIRMED,
            candidates=credible_candidates,
            identity=candidate_to_identity(
                candidate=single_candidate,
                query_name=company_name,
                requested_company_url=company_url,
                user_description=company_description,
            ),
            message=None,
        )

    return IdentityResolutionResult(
        status=IdentityResolutionStatus.AMBIGUOUS,
        candidates=credible_candidates,
        identity=None,
        message=identity_ambiguous_message(
            company_name=company_name,
            language=response_language,
        ),
    )


def find_candidate_by_id(
    candidates: list[CompanyCandidate],
    candidate_id: str,
) -> CompanyCandidate:
    for candidate in candidates:
        if candidate.candidate_id == candidate_id:
            return candidate
    raise ValueError(f"Unknown company candidate_id: {candidate_id}")
