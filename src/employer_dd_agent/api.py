from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from employer_dd_agent.models import (
    IdentityConfirmationRequest,
    ResearchRunResult,
    RunLifecycleStatus,
    RunPhase,
    RunRequest,
    RunResponse,
    RunStartResponse,
    RunStatusResponse,
    utc_now,
)
from employer_dd_agent.run_service import (
    confirm_and_continue_research_run_background,
    continue_research_run_background,
    get_research_run_status,
    resume_research_run,
    run_research_pipeline,
    start_research_run_background,
    validate_identity_confirmation_request,
)


def _raise_runtime_configuration_error(error: RuntimeError) -> None:
    raise HTTPException(status_code=503, detail=str(error)) from error


def _noop_run_complete(
    completed_run_id: UUID,
    result: ResearchRunResult | None,
    error_message: str | None,
) -> None:
    _ = (completed_run_id, result, error_message)


def _build_run_response(run_id: UUID, result: ResearchRunResult) -> RunResponse:
    return RunResponse(
        run_id=run_id,
        created_at=utc_now(),
        identity=result.identity,
        findings=result.findings,
        events=result.events,
        timeline=result.timeline,
        verdict=result.verdict,
        note=(
            "Supervisor-driven deep research with structured events, canonical timeline, "
            "and interview-ready verdict."
        ),
    )


def create_app() -> FastAPI:
    app: FastAPI = FastAPI(title="Employer Due Diligence Agent API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs", response_model=RunResponse | RunStartResponse)
    def create_run(
        request: RunRequest,
        background: bool = Query(default=False),
    ) -> RunResponse | RunStartResponse:
        try:
            if background:
                run_id: UUID = uuid4()
                started_run_id: UUID = start_research_run_background(
                    request=request,
                    run_id=run_id,
                    on_complete=_noop_run_complete,
                )
                return RunStartResponse(
                    run_id=started_run_id,
                    created_at=utc_now(),
                    status=RunLifecycleStatus.RUNNING,
                    phase=RunPhase.PENDING,
                    message="Research run started in background. Poll GET /runs/{run_id} for progress.",
                )

            selected_run_id, result = run_research_pipeline(request=request, run_id=None)
            return _build_run_response(run_id=selected_run_id, result=result)
        except RuntimeError as error:
            _raise_runtime_configuration_error(error)

    @app.post("/runs/{run_id}/identity", response_model=RunStartResponse)
    def confirm_run_identity(
        run_id: UUID,
        request: IdentityConfirmationRequest,
    ) -> RunStartResponse:
        try:
            validate_identity_confirmation_request(
                run_id=run_id,
                candidate_id=request.candidate_id,
            )

            confirm_and_continue_research_run_background(
                run_id=run_id,
                candidate_id=request.candidate_id,
                on_complete=_noop_run_complete,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except RuntimeError as error:
            _raise_runtime_configuration_error(error)

        return RunStartResponse(
            run_id=run_id,
            created_at=utc_now(),
            status=RunLifecycleStatus.RUNNING,
            phase=RunPhase.SUPERVISOR,
            message="Identity confirmed. Research resumed in background.",
        )

    @app.get("/runs/{run_id}", response_model=RunStatusResponse)
    def get_run_status(run_id: UUID) -> RunStatusResponse:
        try:
            return get_research_run_status(run_id=run_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/runs/{run_id}/resume", response_model=RunResponse)
    def resume_run(run_id: UUID) -> RunResponse:
        try:
            result = resume_research_run(run_id=run_id)
        except RuntimeError as error:
            _raise_runtime_configuration_error(error)
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
        return _build_run_response(run_id=run_id, result=result)

    frontend_dist: Path = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app
