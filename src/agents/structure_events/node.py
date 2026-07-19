"""Graph node that structures raw findings into company events before merge."""

from __future__ import annotations

import json
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from agents.graph_state import (
    ResearchRunState,
    dump_company_events,
    load_company_identity,
    load_raw_findings,
    load_run_request,
)
from agents.language import response_language_instruction
from agents.models import CompanyEvent, RawFinding, RunPhase, StructuredCompanyEvents
from agents.prompts import STRUCTURE_EVENTS_PROMPT
from agents.structured_output import invoke_structured_output


def _phase_update(phase: RunPhase) -> dict[str, str]:
    return {"phase": phase.value}


def _truncate_text(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}…"


def _findings_text(findings: list[RawFinding]) -> str:
    max_findings: int = 20
    max_snippet_length: int = 600
    selected_findings: list[RawFinding] = findings[:max_findings]
    serialized_findings: list[dict[str, str]] = []
    for finding in selected_findings:
        serialized_findings.append(
            {
                "source_type": finding.source_type.value,
                "source_url": str(finding.source_url),
                "title": _truncate_text(finding.title, 200),
                "snippet": _truncate_text(finding.snippet, max_snippet_length),
            }
        )
    return json.dumps(serialized_findings, ensure_ascii=False, indent=2)


def structure_events_step(
    state: ResearchRunState,
    config: RunnableConfig,
) -> Command[Literal["merge_timeline"]]:
    """Turn raw findings into grounded company events, then continue to merge."""
    findings: list[RawFinding] = load_raw_findings(state["findings"])
    if not findings:
        return Command(
            goto="merge_timeline",
            update={"events": [], **_phase_update(RunPhase.STRUCTURE_EVENTS)},
        )

    identity = load_company_identity(state["identity"])
    request = load_run_request(state["request"])
    parsed_output = invoke_structured_output(
        config=config,
        model_class=StructuredCompanyEvents,
        prompt=STRUCTURE_EVENTS_PROMPT.format(
            company_name=identity.canonical_name,
            findings_text=_findings_text(findings),
            response_language_instruction=response_language_instruction(
                language=request.response_language
            ),
        ),
    )

    allowed_urls: set[str] = {str(finding.source_url) for finding in findings}
    filtered_events: list[CompanyEvent] = []
    for event in parsed_output.events:
        if str(event.source_url) in allowed_urls:
            filtered_events.append(event)
    return Command(
        goto="merge_timeline",
        update={
            "events": dump_company_events(filtered_events),
            **_phase_update(RunPhase.STRUCTURE_EVENTS),
        },
    )
