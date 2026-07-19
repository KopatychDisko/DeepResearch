from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from agents.models import ToolObservation, ToolObservationStatus


def test_tool_observation_ok_search_json_omits_finding_body_keys() -> None:
    observation = ToolObservation(
        status=ToolObservationStatus.OK,
        tool="search_news",
        summary="Collected findings from news",
        counts={"findings": 3},
        source="news",
    )
    payload: dict[str, object] = observation.model_dump(mode="json")
    serialized: str = json.dumps(payload)
    round_trip: dict[str, object] = json.loads(serialized)

    assert round_trip["status"] == "ok"
    assert round_trip["tool"] == "search_news"
    assert round_trip["summary"] == "Collected findings from news"
    assert round_trip["counts"] == {"findings": 3}
    assert round_trip["source"] == "news"
    assert "title" not in round_trip
    assert "source_url" not in round_trip
    assert "snippet" not in round_trip


def test_tool_observation_error_includes_error_fields() -> None:
    observation = ToolObservation(
        status=ToolObservationStatus.ERROR,
        tool="search_reviews",
        summary="Source search failed after retries",
        error_code="RuntimeError",
        error_message="upstream timeout",
    )
    payload: dict[str, object] = observation.model_dump(mode="json")
    serialized: str = json.dumps(payload)
    round_trip: dict[str, object] = json.loads(serialized)

    assert round_trip["status"] == "error"
    assert round_trip["error_code"] == "RuntimeError"
    assert round_trip["error_message"] == "upstream timeout"


def test_tool_observation_denied_includes_error_fields() -> None:
    observation = ToolObservation(
        status=ToolObservationStatus.DENIED,
        tool="unknown_xyz",
        summary="Tool not permitted",
        error_code="unknown_tool",
        error_message="Tool unknown_xyz is not in the permission matrix",
    )
    payload: dict[str, object] = observation.model_dump(mode="json")
    serialized: str = json.dumps(payload)
    round_trip: dict[str, object] = json.loads(serialized)

    assert round_trip["status"] == "denied"
    assert round_trip["error_code"] == "unknown_tool"
    assert "error_message" in round_trip


def test_tool_observation_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ToolObservation(
            status=ToolObservationStatus.OK,
            tool="think",
            summary="ok",
            title="must not be accepted",
        )
