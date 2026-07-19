"""Static tool permission matrix for authorize-before-execute in the supervisor loop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskClass(str, Enum):
    """Risk tier for a supervisor tool (external read, local read, or control)."""

    EXTERNAL_READ = "external_read"
    READ = "read"
    CONTROL = "control"


TOOL_RISK: dict[str, RiskClass] = {
    "search_news": RiskClass.EXTERNAL_READ,
    "search_reviews": RiskClass.EXTERNAL_READ,
    "search_hh": RiskClass.EXTERNAL_READ,
    "think": RiskClass.READ,
    "finish_research": RiskClass.CONTROL,
}


@dataclass(frozen=True)
class AuthorizeResult:
    """Outcome of a static permission check: allow/deny, risk tier, and reason code."""

    allowed: bool
    risk_class: RiskClass | None
    reason: str


def authorize_tool(tool_name: str) -> AuthorizeResult:
    """Allow or deny a tool using the static risk matrix; unknown tools are denied."""
    risk: RiskClass | None = TOOL_RISK.get(tool_name)
    if risk is None:
        return AuthorizeResult(allowed=False, risk_class=None, reason="unknown_tool")
    return AuthorizeResult(allowed=True, risk_class=risk, reason="allow")
