"""Shared helpers for domain models."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current UTC timestamp for run and retrieval metadata."""
    return datetime.now(UTC)
