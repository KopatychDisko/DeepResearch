from __future__ import annotations

import sqlite3
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver

from agents.configuration import Configuration
from agents.graph_state import dump_company_candidates, dump_company_identity
from agents.identity.resolution import candidate_to_identity
from agents.models import (
    CompanyCandidate,
    Confidence,
    RunLifecycleStatus,
    RunPhase,
    RunRequest,
)
from agents.pipeline import _should_skip_identity_resolution, build_research_graph
from backend.run_service import (
    _build_checkpointer_context,
    _graph_resume_input,
    build_initial_state,
)


def test_should_skip_identity_resolution_after_user_confirmation() -> None:
    run_id = uuid4()
    request = RunRequest(company_name="Яндекс")
    state = build_initial_state(request=request, run_id=run_id)
    candidate = CompanyCandidate(
        candidate_id="abc123",
        name="Яндекс",
        description="IT company",
        website_url="https://yandex.ru",
        confidence=Confidence.HIGH,
    )
    state["status"] = RunLifecycleStatus.RUNNING.value
    state["phase"] = RunPhase.SUPERVISOR.value
    state["identity_candidates"] = []
    state["identity"] = dump_company_identity(
        candidate_to_identity(
            candidate=candidate,
            query_name=request.company_name,
            requested_company_url=None,
            user_description=None,
        )
    )

    assert _should_skip_identity_resolution(state=state) is True


def test_should_not_skip_identity_resolution_while_awaiting_input() -> None:
    run_id = uuid4()
    request = RunRequest(company_name="Яндекс")
    state = build_initial_state(request=request, run_id=run_id)
    state["status"] = RunLifecycleStatus.AWAITING_INPUT.value
    state["phase"] = RunPhase.AWAITING_IDENTITY.value

    assert _should_skip_identity_resolution(state=state) is False


def test_graph_resume_input_after_identity_confirmation() -> None:
    run_id = uuid4()
    request = RunRequest(company_name="Яндекс")
    state = build_initial_state(request=request, run_id=run_id)
    candidate = CompanyCandidate(
        candidate_id="abc123",
        name="Яндекс",
        description="IT company",
        website_url="https://yandex.ru",
        confidence=Confidence.HIGH,
    )
    state["status"] = RunLifecycleStatus.RUNNING.value
    state["phase"] = RunPhase.SUPERVISOR.value
    state["identity_candidates"] = []
    state["identity"] = dump_company_identity(
        candidate_to_identity(
            candidate=candidate,
            query_name=request.company_name,
            requested_company_url=None,
            user_description=None,
        )
    )

    resume_input = _graph_resume_input(state=state, next_nodes=())
    assert resume_input is not None
    assert resume_input.goto == "supervisor"


def test_identity_confirmation_marks_resume_pending_state() -> None:
    run_id = uuid4()
    request = RunRequest(company_name="Яндекс")
    state = build_initial_state(request=request, run_id=run_id)
    candidate = CompanyCandidate(
        candidate_id="abc123",
        name="Яндекс",
        description="IT company",
        website_url="https://yandex.ru",
        confidence=Confidence.HIGH,
    )
    state["status"] = RunLifecycleStatus.AWAITING_INPUT.value
    state["phase"] = RunPhase.AWAITING_IDENTITY.value
    state["identity_candidates"] = dump_company_candidates([candidate])

    settings = Configuration()
    execution_context = _build_checkpointer_context(settings=settings, run_id=run_id)
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(connection)
    checkpointer.setup()
    graph = build_research_graph().compile(checkpointer=checkpointer)
    graph.update_state(execution_context.run_config, state, as_node="resolve_identity")

    graph.update_state(
        execution_context.run_config,
        {
            "identity": dump_company_identity(
                candidate_to_identity(
                    candidate=candidate,
                    query_name=request.company_name,
                    requested_company_url=None,
                    user_description=None,
                )
            ),
            "identity_candidates": [],
            "status": RunLifecycleStatus.RUNNING.value,
            "phase": RunPhase.SUPERVISOR.value,
            "error_message": None,
        },
    )

    snapshot = graph.get_state(execution_context.run_config)
    assert snapshot.values["status"] == RunLifecycleStatus.RUNNING.value
    assert snapshot.values["phase"] == RunPhase.SUPERVISOR.value
    assert snapshot.values["identity_candidates"] == []
    assert _graph_resume_input(state=snapshot.values, next_nodes=tuple(snapshot.next or ())) is not None or snapshot.next == (
        "resolve_identity",
    )
