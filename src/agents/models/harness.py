"""Supervisor harness tool observation contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from agents.models.enums import ToolObservationStatus


class ToolObservation(BaseModel):
    """Structured tool outcome the harness writes into ToolMessage content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ToolObservationStatus
    tool: str
    summary: str
    counts: dict[str, int] | None = None
    source: str | None = None
    error_code: str | None = None
    error_message: str | None = None
