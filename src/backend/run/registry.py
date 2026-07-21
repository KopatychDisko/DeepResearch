"""In-memory run status registry for background research workers."""

from __future__ import annotations

import threading
from uuid import UUID

from agents.models import RunLifecycleStatus

_run_lock: threading.Lock = threading.Lock()
_run_status_by_id: dict[UUID, RunLifecycleStatus] = {}
_run_errors_by_id: dict[UUID, str] = {}
_run_company_name_by_id: dict[UUID, str] = {}


def set_run_status(
    run_id: UUID,
    status: RunLifecycleStatus,
    error_message: str | None,
) -> None:
    """Update tracked lifecycle status and optional error message for a run."""
    with _run_lock:
        _run_status_by_id[run_id] = status
        if error_message is None:
            _run_errors_by_id.pop(run_id, None)
        else:
            _run_errors_by_id[run_id] = error_message


def register_run_metadata(run_id: UUID, company_name: str) -> None:
    """Mark a run as running and store its company name before the worker starts."""
    with _run_lock:
        _run_company_name_by_id[run_id] = company_name
        _run_status_by_id[run_id] = RunLifecycleStatus.RUNNING
        _run_errors_by_id.pop(run_id, None)


def get_run_company_name(run_id: UUID) -> str:
    """Return the company name registered for a run, or an empty string."""
    with _run_lock:
        return _run_company_name_by_id.get(run_id, "")


def get_run_status(run_id: UUID) -> RunLifecycleStatus | None:
    """Return the tracked lifecycle status for a run, if known."""
    with _run_lock:
        return _run_status_by_id.get(run_id)


def get_run_error(run_id: UUID) -> str | None:
    """Return the tracked error message for a failed run, if any."""
    with _run_lock:
        return _run_errors_by_id.get(run_id)
