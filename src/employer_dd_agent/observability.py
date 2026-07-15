from __future__ import annotations

import atexit
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TypeVar
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler
from langfuse import Langfuse, get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

from employer_dd_agent.configuration import Configuration
from employer_dd_agent.models import ResponseLanguage, RunRequest, SourceType

ReturnType = TypeVar("ReturnType")

_initialized_public_key: str | None = None
_observability_shutdown_registered: bool = False


def is_langfuse_configured() -> bool:
    public_key: str | None = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key: str | None = os.environ.get("LANGFUSE_SECRET_KEY")
    return public_key is not None and secret_key is not None


def _register_shutdown_hook() -> None:
    global _observability_shutdown_registered
    if _observability_shutdown_registered:
        return
    atexit.register(flush_langfuse)
    _observability_shutdown_registered = True


def _ensure_langfuse_initialized() -> bool:
    global _initialized_public_key

    if not is_langfuse_configured():
        return False

    public_key: str = os.environ["LANGFUSE_PUBLIC_KEY"]
    if _initialized_public_key == public_key:
        return True

    if os.environ.get("LANGFUSE_RELEASE") is None:
        os.environ["LANGFUSE_RELEASE"] = "employer-dd-agent@0.1.0"

    Langfuse()
    _initialized_public_key = public_key
    _register_shutdown_hook()
    return True


def initialize_observability() -> None:
    """Initialize Langfuse after environment variables are loaded."""
    _ensure_langfuse_initialized()


def flush_langfuse() -> None:
    if not is_langfuse_configured():
        return
    if not _ensure_langfuse_initialized():
        return
    get_client().flush()


def build_langfuse_run_metadata(
    *,
    run_id: UUID,
    request: RunRequest,
) -> dict[str, object]:
    tags: list[str] = [
        "employer-dd",
        f"lang:{request.response_language.value}",
    ]
    return {
        "langfuse_session_id": str(run_id),
        "langfuse_tags": tags,
    }


def build_langfuse_run_name(request: RunRequest) -> str:
    return f"employer-dd:{request.company_name}"


def build_langfuse_trace_input(request: RunRequest) -> dict[str, str | None]:
    trace_input: dict[str, str | None] = {
        "company_name": request.company_name,
        "response_language": request.response_language.value,
        "company_url": str(request.company_url) if request.company_url is not None else None,
    }
    if request.company_description is not None:
        trace_input["company_description"] = request.company_description
    return trace_input


@contextmanager
def trace_research_run(
    *,
    run_id: UUID,
    request: RunRequest,
) -> Iterator[BaseCallbackHandler | None]:
    settings = Configuration()
    if not settings.langfuse_tracing_enabled or not _ensure_langfuse_initialized():
        yield None
        return

    langfuse_client = get_client()
    trace_id: str = Langfuse.create_trace_id(seed=str(run_id))
    trace_name: str = build_langfuse_run_name(request=request)
    session_id: str = str(run_id)
    tags: list[str] = [
        "employer-dd",
        f"lang:{request.response_language.value}",
    ]

    with langfuse_client.start_as_current_observation(
        as_type="span",
        name="employer-dd-research-run",
        trace_context={"trace_id": trace_id},
    ) as root_span:
        root_span.update(input=build_langfuse_trace_input(request=request))
        with propagate_attributes(
            trace_name=trace_name,
            session_id=session_id,
            tags=tags,
            metadata={"run_id": session_id},
        ):
            handler: CallbackHandler = CallbackHandler()
            try:
                yield handler
            finally:
                flush_langfuse()


def get_langfuse_handler() -> BaseCallbackHandler | None:
    if not _ensure_langfuse_initialized():
        return None
    return CallbackHandler()


def trace_source_research(
    source_type: SourceType,
    company_name: str,
    response_language: ResponseLanguage,
    action: Callable[[], ReturnType],
) -> ReturnType:
    settings = Configuration()
    if not settings.langfuse_tracing_enabled or not _ensure_langfuse_initialized():
        return action()

    langfuse_client = get_client()
    span_name: str = f"source_research_{source_type.value}"
    with langfuse_client.start_as_current_observation(
        name=span_name,
        as_type="span",
    ) as span:
        span.update(
            input={
                "source_type": source_type.value,
                "company_name": company_name,
                "response_language": response_language.value,
            }
        )
        result: ReturnType = action()
        findings_count: int = 0
        if isinstance(result, list):
            findings_count = len(result)
        span.update(
            output={
                "findings_count": findings_count,
            }
        )
        return result
