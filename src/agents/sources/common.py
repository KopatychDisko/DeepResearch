from __future__ import annotations

from langchain_tavily import TavilySearch

from agents.configuration import Configuration
from agents.models import (
    CompanyIdentity,
    RawFinding,
    RetrievalMetadata,
    SourceType,
    utc_now,
)


def _source_topic(source_type: SourceType) -> str:
    if source_type is SourceType.NEWS:
        return "company news and press releases"
    if source_type is SourceType.REVIEWS:
        return "employee reviews and workplace reputation"
    if source_type is SourceType.HH:
        return "job postings and hiring footprint on hh.ru"
    raise ValueError(f"Unsupported source type: {source_type}")


def _source_query(source_type: SourceType, identity: CompanyIdentity) -> str:
    topic: str = _source_topic(source_type)
    description_part: str = ""
    if identity.user_description is not None:
        description_part = f" {identity.user_description}"
    if identity.company_url is not None:
        from agents.identity.resolution import normalize_host

        host: str = normalize_host(str(identity.company_url))
        return f"{identity.canonical_name}{description_part} site:{host} {topic} ru"
    return f"{identity.canonical_name}{description_part} {topic} ru"


def _result_to_finding(source_type: SourceType, result: dict[str, object]) -> RawFinding:
    url_value = result.get("url")
    if not isinstance(url_value, str):
        raise ValueError(f"Missing URL in Tavily result for {source_type.value}")

    title_value = result.get("title")
    if not isinstance(title_value, str):
        title_value = f"{source_type.value} finding"

    content_value = result.get("content")
    if not isinstance(content_value, str):
        content_value = ""

    metadata: RetrievalMetadata = RetrievalMetadata(
        fetched_at=utc_now(),
        source_label=source_type.value,
        note="Collected by Tavily source search",
    )
    return RawFinding(
        source_type=source_type,
        source_url=url_value,
        title=title_value,
        snippet=content_value,
        metadata=metadata,
    )


def search_web(query: str, max_results: int) -> list[dict[str, object]]:
    return _search_with_tavily(query=query, max_results=max_results)


def _search_with_tavily(query: str, max_results: int) -> list[dict[str, object]]:
    tavily = TavilySearch(max_results=max_results, topic="general", include_raw_content=False)
    max_attempts: int = 3
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            raw_result: dict[str, object] = tavily.invoke({"query": query})
            results_value = raw_result.get("results")
            if not isinstance(results_value, list):
                raise ValueError("Tavily returned invalid results payload")
            typed_results: list[dict[str, object]] = []
            for item in results_value:
                if isinstance(item, dict):
                    typed_results.append(item)
            return typed_results
        except Exception as error:
            last_error = error
            if attempt < max_attempts:
                print(
                    f"Warning: Tavily request retry {attempt}/{max_attempts - 1}",
                    {
                        "query": query,
                        "error_type": type(error).__name__,
                    },
                )
    if last_error is None:
        raise RuntimeError("Tavily search failed with unknown error state")
    raise RuntimeError(f"Tavily search failed after retries for query={query!r}") from last_error


def _search_source_with_tavily(source_type: SourceType, query: str, max_results: int) -> list[dict[str, object]]:
    return _search_with_tavily(query=query, max_results=max_results)


def fetch_source_findings(
    source_type: SourceType,
    identity: CompanyIdentity,
    settings: Configuration,
) -> list[RawFinding]:
    query: str = _source_query(source_type, identity)
    result_items: list[dict[str, object]] = _search_source_with_tavily(
        source_type=source_type,
        query=query,
        max_results=settings.tavily_max_results,
    )
    findings: list[RawFinding] = []
    for item in result_items:
        findings.append(_result_to_finding(source_type, item))
    return findings


def fetch_news(identity: CompanyIdentity, settings: Configuration) -> list[RawFinding]:
    return fetch_source_findings(source_type=SourceType.NEWS, identity=identity, settings=settings)


def fetch_reviews(identity: CompanyIdentity, settings: Configuration) -> list[RawFinding]:
    return fetch_source_findings(source_type=SourceType.REVIEWS, identity=identity, settings=settings)


def fetch_hh(identity: CompanyIdentity, settings: Configuration) -> list[RawFinding]:
    return fetch_source_findings(source_type=SourceType.HH, identity=identity, settings=settings)
