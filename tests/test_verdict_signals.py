from __future__ import annotations

from employer_dd_agent.models import (
    CanonicalTimeline,
    CanonicalTimelineEvent,
    Confidence,
    EventCategory,
    ResponseLanguage,
    TimelineConflict,
)
from employer_dd_agent.verdict import build_risks_from_timeline, build_red_flags_from_timeline


def _event(
    category: EventCategory,
    description: str,
    confidence: Confidence = Confidence.HIGH,
) -> CanonicalTimelineEvent:
    return CanonicalTimelineEvent(
        date="2024-01-01",
        category=category,
        description=description,
        source_urls=["https://example.com/article"],
        confidence=confidence,
        has_date_conflict=False,
    )


def test_red_flags_only_for_severe_categories() -> None:
    timeline = CanonicalTimeline(
        events=[
            _event(EventCategory.PRODUCT, "Запуск нового сервиса"),
            _event(EventCategory.LAYOFFS, "Сокращение 10% штата"),
            _event(EventCategory.SCANDAL, "Расследование регулятора"),
        ],
        conflicts=[],
    )
    flags: list[str] = build_red_flags_from_timeline(
        timeline=timeline,
        language=ResponseLanguage.RU,
    )
    assert len(flags) == 2
    assert any("Сокращение" in flag for flag in flags)
    assert any("Расследование" in flag for flag in flags)


def test_risks_empty_when_timeline_is_positive_only() -> None:
    timeline = CanonicalTimeline(
        events=[
            _event(EventCategory.PRODUCT, "Новый продукт"),
            _event(EventCategory.FUNDING, "Раунд инвестиций"),
        ],
        conflicts=[],
    )
    risks: list[str] = build_risks_from_timeline(
        timeline=timeline,
        language=ResponseLanguage.RU,
    )
    assert risks == []


def test_risks_from_leadership_reviews_and_conflicts() -> None:
    timeline = CanonicalTimeline(
        events=[
            _event(EventCategory.LEADERSHIP, "Смена CEO"),
            _event(EventCategory.REVIEW_SIGNAL, "Смешанные отзывы о переработках"),
        ],
        conflicts=[
            TimelineConflict(
                category=EventCategory.LEADERSHIP,
                message="Разные даты смены руководства",
                source_urls=["https://example.com/a", "https://example.com/b"],
                dates=["2023", "2024"],
            )
        ],
    )
    risks: list[str] = build_risks_from_timeline(
        timeline=timeline,
        language=ResponseLanguage.RU,
    )
    assert len(risks) == 3
    assert any("CEO" in risk for risk in risks)
    assert any("отзывы" in risk for risk in risks)
    assert any("даты" in risk for risk in risks)
