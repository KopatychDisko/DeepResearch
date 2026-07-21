"""Supervisor loop budget checks and token estimation."""

from __future__ import annotations

import time
from typing import Literal

import tiktoken
from langchain_core.messages import AIMessage
from langgraph.types import Command

from agents.configuration import Configuration
from agents.graph.state import ResearchRunState
from agents.observability import record_budget_stop_reason

_TIKTOKEN_ENCODING_NAME: str = "cl100k_base"


def estimate_text_tokens(text: str) -> int:
    """Estimate token count for a text string using cl100k_base encoding."""
    encoding = tiktoken.get_encoding(_TIKTOKEN_ENCODING_NAME)
    return len(encoding.encode(text))


def tokens_from_supervisor_turn(
    response: AIMessage,
    prompt_texts: list[str],
) -> int:
    """Return token usage for one supervisor turn from metadata or estimation."""
    usage_metadata = response.usage_metadata
    if usage_metadata is not None:
        total_tokens = usage_metadata.get("total_tokens")
        if total_tokens is not None:
            return int(total_tokens)
        input_tokens = usage_metadata.get("input_tokens")
        output_tokens = usage_metadata.get("output_tokens")
        if input_tokens is not None and output_tokens is not None:
            return int(input_tokens) + int(output_tokens)
    prompt_token_count: int = sum(estimate_text_tokens(text) for text in prompt_texts)
    response_token_count: int = estimate_text_tokens(str(response.content))
    return prompt_token_count + response_token_count


def budget_stop_command(
    budget_stop_reason: str,
    extra_update: dict[str, object],
) -> Command[Literal["structure_events"]]:
    """Stop the supervisor loop and route to structure_events with a stop reason."""
    record_budget_stop_reason(budget_stop_reason=budget_stop_reason)
    return Command(
        goto="structure_events",
        update={
            **extra_update,
            "budget_stop_reason": budget_stop_reason,
        },
    )


def resolve_budget_deadline(
    state: ResearchRunState,
    settings: Configuration,
) -> tuple[float, dict[str, object]]:
    """Return the wall-clock deadline and any state update needed to set it."""
    now: float = time.time()
    deadline: float | None = state.get("budget_deadline_unix")
    budget_state_update: dict[str, object] = {}
    if deadline is None:
        deadline = now + float(settings.max_run_wall_clock_seconds)
        budget_state_update["budget_deadline_unix"] = deadline
    return deadline, budget_state_update


def budget_exhausted(
    state: ResearchRunState,
    settings: Configuration,
    deadline: float,
) -> str | None:
    """Return a budget stop reason when any harness limit is reached, else None."""
    if state["iteration_count"] >= settings.max_tool_iterations:
        return "max_tool_iterations"
    if time.time() >= deadline:
        return "wall_clock"
    estimated_tokens_used: int = int(state.get("estimated_tokens_used") or 0)
    if estimated_tokens_used >= settings.max_estimated_run_tokens:
        return "soft_token_budget"
    return None
