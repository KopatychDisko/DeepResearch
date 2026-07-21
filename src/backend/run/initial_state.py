"""Initial LangGraph state for a new research run."""

from __future__ import annotations

from uuid import UUID

from agents.graph.state import (
    ResearchRunState,
    dump_canonical_timeline,
    dump_company_identity,
    dump_employer_verdict,
    dump_hh_vacancy_analysis,
    dump_run_request,
)
from agents.hh_vacancies.analysis import build_pending_hh_vacancy_analysis
from agents.identity.resolution import normalize_company_name
from agents.models import (
    CanonicalTimeline,
    CompanyIdentity,
    RunLifecycleStatus,
    RunPhase,
    RunRequest,
)
from agents.verdict.verdict import build_insufficient_data_verdict


def build_initial_state(request: RunRequest, run_id: UUID) -> ResearchRunState:
    """Build the initial ResearchRunState with a placeholder identity and empty findings."""
    placeholder_identity = CompanyIdentity(
        query_name=request.company_name,
        canonical_name=request.company_name,
        normalized_name=normalize_company_name(request.company_name),
        company_url=request.company_url,
        profile_summary=None,
        user_description=request.company_description,
    )
    return {
        "run_id": str(run_id),
        "phase": RunPhase.PENDING.value,
        "status": RunLifecycleStatus.RUNNING.value,
        "error_message": None,
        "request": dump_run_request(request),
        "identity": dump_company_identity(placeholder_identity),
        "identity_candidates": [],
        "findings": [],
        "events": [],
        "timeline": dump_canonical_timeline(CanonicalTimeline(events=[], conflicts=[])),
        "verdict": dump_employer_verdict(
            build_insufficient_data_verdict(
                company_name=request.company_name,
                language=request.response_language,
            )
        ),
        "hh_vacancy_analysis": dump_hh_vacancy_analysis(
            build_pending_hh_vacancy_analysis(search_query=request.company_name)
        ),
        "completed_sources": [],
        "conversation_history": [],
        "iteration_count": 0,
        "finished": False,
        "budget_deadline_unix": None,
        "estimated_tokens_used": 0,
        "budget_stop_reason": None,
    }
