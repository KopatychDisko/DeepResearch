"""Prompt context formatting for the supervisor research loop."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, ToolMessage

from agents.models import CompanyIdentity, ResponseLanguage, SourceType


def completed_sources_text(completed_sources: list[SourceType]) -> str:
    """Format completed source types for the supervisor system prompt."""
    if not completed_sources:
        return "none"
    return ", ".join(source.value for source in completed_sources)


def company_context_text(identity: CompanyIdentity, language: ResponseLanguage) -> str:
    """Format identity profile fields for the supervisor system prompt."""
    context_parts: list[str] = []
    if identity.profile_summary is not None:
        context_parts.append(identity.profile_summary)
    if identity.user_description is not None:
        if language == ResponseLanguage.EN:
            context_parts.append(f"User note: {identity.user_description}")
        else:
            context_parts.append(f"Уточнение от пользователя: {identity.user_description}")
    if identity.company_url is not None:
        if language == ResponseLanguage.EN:
            context_parts.append(f"Website: {identity.company_url}")
        else:
            context_parts.append(f"Сайт: {identity.company_url}")
    if not context_parts:
        if language == ResponseLanguage.EN:
            return "not provided"
        return "не указан"
    return " | ".join(context_parts)


def format_recent_tool_outcomes(
    conversation_history: list[AIMessage | ToolMessage],
    max_outcomes: int,
) -> str:
    """Format the most recent tool observation summaries for the supervisor prompt."""
    tool_messages: list[ToolMessage] = [
        message for message in conversation_history if isinstance(message, ToolMessage)
    ]
    if not tool_messages:
        return "none"
    recent_messages: list[ToolMessage] = tool_messages[-max_outcomes:]
    lines: list[str] = []
    for message in recent_messages:
        payload: dict[str, object]
        try:
            parsed = json.loads(str(message.content))
        except json.JSONDecodeError:
            lines.append(f"- status=unknown tool={message.name or 'unknown'} summary={message.content}")
            continue
        if not isinstance(parsed, dict):
            lines.append(f"- status=unknown tool={message.name or 'unknown'} summary={message.content}")
            continue
        payload = parsed
        status_value = payload.get("status", "unknown")
        tool_value = payload.get("tool", message.name or "unknown")
        summary_value = payload.get("summary", "")
        lines.append(f"- status={status_value} tool={tool_value} summary={summary_value}")
    return "\n".join(lines)
