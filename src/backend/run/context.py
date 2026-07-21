"""RunnableConfig assembly for one research run invocation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig

from agents.configuration import Configuration
from agents.model_credentials import (
    ResolvedLlmModel,
    load_model_credentials,
    require_model_credentials,
    resolve_llm_model,
)
from agents.models import RunRequest
from agents.observability import build_langfuse_run_metadata, build_langfuse_run_name


@dataclass(frozen=True)
class RunExecutionContext:
    """RunnableConfig plus thread id for one research run against the checkpointer."""

    run_id: UUID
    thread_id: str
    run_config: RunnableConfig


def build_run_configurable(
    settings: Configuration,
    run_id: UUID,
    resolved_model: ResolvedLlmModel,
) -> dict[str, object]:
    """Build the configurable dict passed into LangGraph RunnableConfig."""
    return {
        "thread_id": str(run_id),
        "llm_model": resolved_model.model_name,
        "api_key": resolved_model.api_key,
        "structured_llm_max_tokens": settings.structured_llm_max_tokens,
        "tools_llm_max_tokens": settings.tools_llm_max_tokens,
        "max_tool_iterations": settings.max_tool_iterations,
        "max_run_wall_clock_seconds": settings.max_run_wall_clock_seconds,
        "max_estimated_run_tokens": settings.max_estimated_run_tokens,
    }


def build_run_execution_context(
    settings: Configuration,
    run_id: UUID,
    request: RunRequest | None,
    langfuse_handler: BaseCallbackHandler | None,
) -> RunExecutionContext:
    """Resolve credentials and assemble RunnableConfig for graph invoke."""
    credentials = load_model_credentials()
    require_model_credentials(credentials=credentials)
    resolved_model = resolve_llm_model(
        configured_model=settings.llm_model,
        credentials=credentials,
    )
    callbacks: list[BaseCallbackHandler] = []
    if langfuse_handler is not None and settings.langfuse_tracing_enabled:
        callbacks.append(langfuse_handler)
    thread_id: str = str(run_id)
    recursion_limit: int = (2 * settings.max_tool_iterations) + 12
    run_config: RunnableConfig = {
        "configurable": build_run_configurable(
            settings=settings,
            run_id=run_id,
            resolved_model=resolved_model,
        ),
        "callbacks": callbacks,
        "recursion_limit": recursion_limit,
    }
    if request is not None:
        run_config["metadata"] = build_langfuse_run_metadata(run_id=run_id, request=request)
        run_config["run_name"] = build_langfuse_run_name(request=request)
    return RunExecutionContext(run_id=run_id, thread_id=thread_id, run_config=run_config)


def build_checkpointer_context(settings: Configuration, run_id: UUID) -> RunExecutionContext:
    """Build execution context for checkpoint reads without Langfuse metadata."""
    return build_run_execution_context(
        settings=settings,
        run_id=run_id,
        request=None,
        langfuse_handler=None,
    )
