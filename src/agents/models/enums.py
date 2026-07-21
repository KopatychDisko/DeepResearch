"""Shared enumerations for research runs, events, and API responses."""

from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    """Research source channel used by supervisor search tools."""

    NEWS = "news"
    REVIEWS = "reviews"
    HH = "hh"


class Confidence(str, Enum):
    """Evidence confidence level for findings and events."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResponseLanguage(str, Enum):
    """Language for user-facing research output."""

    RU = "ru"
    EN = "en"


class EventCategory(str, Enum):
    """Canonical event category for timeline items."""

    FUNDING = "funding"
    LEADERSHIP = "leadership"
    LAYOFFS = "layoffs"
    SCANDAL = "scandal"
    PRODUCT = "product"
    REVIEW_SIGNAL = "review_signal"


class VerdictColor(str, Enum):
    """High-level employer risk signal for the verdict card."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class RunPhase(str, Enum):
    """Pipeline phase reported for run progress and status APIs."""

    PENDING = "pending"
    RESOLVE_IDENTITY = "resolve_identity"
    AWAITING_IDENTITY = "awaiting_identity"
    ANALYZE_HH_VACANCIES = "analyze_hh_vacancies"
    SUPERVISOR = "supervisor"
    STRUCTURE_EVENTS = "structure_events"
    MERGE_TIMELINE = "merge_timeline"
    GENERATE_VERDICT = "generate_verdict"
    COMPLETED = "completed"


class RunLifecycleStatus(str, Enum):
    """Lifecycle status of a research run for API clients."""

    RUNNING = "running"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ToolObservationStatus(str, Enum):
    """Outcome status carried in harness ToolObservation JSON messages."""

    OK = "ok"
    ERROR = "error"
    DENIED = "denied"


class HhVacancyStatus(str, Enum):
    """Outcome status for hh.ru vacancy analysis blocks."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    ERROR = "error"
