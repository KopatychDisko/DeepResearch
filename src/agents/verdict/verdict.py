from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from agents.language import (
    data_conflict_label,
    event_category_label,
    insufficient_data_score_explanation,
    insufficient_data_summary,
    response_language_instruction,
)
from agents.models import (
    CanonicalTimeline,
    EmployerVerdict,
    EventCategory,
    ResponseLanguage,
    StructuredEmployerVerdict,
    VerdictColor,
    VerdictEvidenceLink,
)
from agents.prompts import VERDICT_PROMPT
from agents.structured_output import invoke_structured_output

_RED_FLAG_CATEGORIES: frozenset[EventCategory] = frozenset(
    {EventCategory.LAYOFFS, EventCategory.SCANDAL}
)
_RISK_CATEGORIES: frozenset[EventCategory] = frozenset(
    {EventCategory.LEADERSHIP, EventCategory.REVIEW_SIGNAL}
)


def build_evidence_links(timeline: CanonicalTimeline) -> list[VerdictEvidenceLink]:
    evidence_links: list[VerdictEvidenceLink] = []
    for event in timeline.events:
        evidence_links.append(
            VerdictEvidenceLink(
                event_description=event.description,
                category=event.category,
                confidence=event.confidence,
                source_urls=event.source_urls,
                date=event.date,
            )
        )
    return evidence_links


def build_red_flags_from_timeline(
    timeline: CanonicalTimeline,
    language: ResponseLanguage,
) -> list[str]:
    red_flags: list[str] = []
    seen_descriptions: set[str] = set()
    for event in timeline.events:
        if event.category not in _RED_FLAG_CATEGORIES:
            continue
        if event.description in seen_descriptions:
            continue
        seen_descriptions.add(event.description)
        category_label: str = event_category_label(category=event.category, language=language)
        red_flags.append(f"{category_label}: {event.description}")
    return red_flags


def build_risks_from_timeline(
    timeline: CanonicalTimeline,
    language: ResponseLanguage,
) -> list[str]:
    risks: list[str] = []
    seen_descriptions: set[str] = set()
    for event in timeline.events:
        if event.category not in _RISK_CATEGORIES:
            continue
        if event.description in seen_descriptions:
            continue
        seen_descriptions.add(event.description)
        category_label: str = event_category_label(category=event.category, language=language)
        risks.append(f"{category_label}: {event.description}")
    conflict_label: str = data_conflict_label(language=language)
    for conflict in timeline.conflicts:
        risks.append(f"{conflict_label}: {conflict.message}")
    return risks


def _timeline_text(timeline: CanonicalTimeline) -> str:
    serialized_events: list[dict[str, object]] = []
    for event in timeline.events:
        serialized_events.append(
            {
                "date": event.date,
                "category": event.category.value,
                "description": event.description,
                "confidence": event.confidence.value,
                "source_urls": [str(url) for url in event.source_urls],
                "has_date_conflict": event.has_date_conflict,
            }
        )
    serialized_conflicts: list[dict[str, object]] = []
    for conflict in timeline.conflicts:
        serialized_conflicts.append(
            {
                "category": conflict.category.value,
                "message": conflict.message,
                "dates": conflict.dates,
                "source_urls": [str(url) for url in conflict.source_urls],
            }
        )
    return json.dumps(
        {"events": serialized_events, "conflicts": serialized_conflicts},
        ensure_ascii=False,
        indent=2,
    )


def build_insufficient_data_verdict(
    company_name: str,
    language: ResponseLanguage,
) -> EmployerVerdict:
    return EmployerVerdict(
        color=VerdictColor.YELLOW,
        score=5,
        score_explanation=insufficient_data_score_explanation(language=language),
        summary=insufficient_data_summary(company_name=company_name, language=language),
        risks=[],
        red_flags=[],
        interesting_facts=[],
        evidence_links=[],
    )


def generate_employer_verdict(
    company_name: str,
    timeline: CanonicalTimeline,
    language: ResponseLanguage,
    config: RunnableConfig,
) -> EmployerVerdict:
    if not timeline.events:
        return build_insufficient_data_verdict(company_name=company_name, language=language)

    parsed_output = invoke_structured_output(
        config=config,
        model_class=StructuredEmployerVerdict,
        prompt=VERDICT_PROMPT.format(
            company_name=company_name,
            timeline_text=_timeline_text(timeline),
            response_language_instruction=response_language_instruction(language=language),
        ),
    )

    return EmployerVerdict(
        color=parsed_output.color,
        score=parsed_output.score,
        score_explanation=parsed_output.score_explanation,
        summary=parsed_output.summary,
        risks=build_risks_from_timeline(timeline=timeline, language=language),
        red_flags=build_red_flags_from_timeline(timeline=timeline, language=language),
        interesting_facts=parsed_output.interesting_facts,
        evidence_links=build_evidence_links(timeline=timeline),
    )
