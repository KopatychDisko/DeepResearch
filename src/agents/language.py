"""Localized labels and user-facing copy for EN/RU response language."""

from __future__ import annotations

from agents.models import EventCategory, ResponseLanguage


def parse_response_language(value: str) -> ResponseLanguage:
    """Parse a language string into ResponseLanguage or raise ValueError."""
    normalized: str = value.strip().lower()
    if normalized == ResponseLanguage.EN.value:
        return ResponseLanguage.EN
    if normalized == ResponseLanguage.RU.value:
        return ResponseLanguage.RU
    raise ValueError(f"Unsupported response language: {value}")


def response_language_instruction(language: ResponseLanguage) -> str:
    """Return the system prompt line that forces user-facing fields into the chosen language."""
    if language == ResponseLanguage.EN:
        return "Write all user-facing text fields in English."
    return "Write all user-facing text fields in Russian."


def event_category_label(category: EventCategory, language: ResponseLanguage) -> str:
    """Return the display label for an event category in the chosen language."""
    labels_ru: dict[EventCategory, str] = {
        EventCategory.LAYOFFS: "Сокращения",
        EventCategory.SCANDAL: "Скандал",
        EventCategory.LEADERSHIP: "Руководство",
        EventCategory.REVIEW_SIGNAL: "Сигнал из отзывов",
        EventCategory.FUNDING: "Финансы",
        EventCategory.PRODUCT: "Продукт",
    }
    labels_en: dict[EventCategory, str] = {
        EventCategory.LAYOFFS: "Layoffs",
        EventCategory.SCANDAL: "Scandal",
        EventCategory.LEADERSHIP: "Leadership",
        EventCategory.REVIEW_SIGNAL: "Review signal",
        EventCategory.FUNDING: "Funding",
        EventCategory.PRODUCT: "Product",
    }
    if language == ResponseLanguage.EN:
        return labels_en[category]
    return labels_ru[category]


def data_conflict_label(language: ResponseLanguage) -> str:
    """Return the localized label used when merged events conflict."""
    if language == ResponseLanguage.EN:
        return "Data conflict"
    return "Конфликт данных"


def insufficient_data_score_explanation(language: ResponseLanguage) -> str:
    """Return the localized short explanation for an insufficient-data score."""
    if language == ResponseLanguage.EN:
        return "Not enough confirmed events for a confident score."
    return "Недостаточно подтверждённых событий для уверенной оценки."


def insufficient_data_summary(company_name: str, language: ResponseLanguage) -> str:
    """Return the localized verdict summary when too few events were confirmed."""
    if language == ResponseLanguage.EN:
        return (
            f"Not enough confirmed events were collected for «{company_name}» "
            "to produce a confident verdict."
        )
    return (
        f"По компании «{company_name}» собрано недостаточно подтверждённых событий "
        "для уверенного вывода."
    )


def identity_not_found_message(company_name: str, language: ResponseLanguage) -> str:
    """Return the localized message when no company match is found."""
    if language == ResponseLanguage.EN:
        return (
            f"Company «{company_name}» was not found in open sources. "
            "Check the name, add a website URL, or a short company description."
        )
    return (
        f"Компания «{company_name}» не найдена в открытых источниках. "
        "Проверьте название, добавьте ссылку на сайт или краткое описание компании."
    )


def identity_unconfirmed_message(company_name: str, language: ResponseLanguage) -> str:
    """Return the localized message when company existence cannot be confirmed."""
    if language == ResponseLanguage.EN:
        return (
            f"Could not confirm that «{company_name}» exists. "
            "Refine the name, add a website URL, or a business description."
        )
    return (
        f"Не удалось подтвердить существование компании «{company_name}». "
        "Уточните название, добавьте ссылку на сайт или описание деятельности."
    )


def identity_ambiguous_message(company_name: str, language: ResponseLanguage) -> str:
    """Return the localized message prompting the user to pick among matches."""
    if language == ResponseLanguage.EN:
        return (
            f"Multiple companies match «{company_name}». "
            "Please choose the correct one from the list."
        )
    return (
        f"Найдено несколько компаний по запросу «{company_name}». "
        "Выберите нужную из списка."
    )


def optional_url_placeholder(language: ResponseLanguage) -> str:
    """Return the localized placeholder when an optional URL was omitted."""
    if language == ResponseLanguage.EN:
        return "not provided"
    return "не указана"


def optional_description_placeholder(language: ResponseLanguage) -> str:
    """Return the localized placeholder when an optional description was omitted."""
    if language == ResponseLanguage.EN:
        return "not provided"
    return "не указано"


def hh_employer_rating_text(language: ResponseLanguage, average_score: float) -> str:
    """Return localized employer rating summary text for hh.ru blocks."""
    if language == ResponseLanguage.EN:
        return f"Employer rating on hh.ru: {average_score}/5."
    return f"Рейтинг работодателя на hh.ru: {average_score}/5."


def hh_employer_rating_unavailable(language: ResponseLanguage) -> str:
    """Return localized text when hh.ru employer rating is unavailable."""
    if language == ResponseLanguage.EN:
        return "Employer rating on hh.ru is unavailable."
    return "Рейтинг работодателя на hh.ru недоступен."


def hh_no_active_vacancies(language: ResponseLanguage) -> str:
    """Return localized salary summary when employer has no active vacancies."""
    if language == ResponseLanguage.EN:
        return "No active vacancies are listed on hh.ru for this employer."
    return "У работодателя нет активных вакансий на hh.ru."


def hh_no_conditions_to_summarize(language: ResponseLanguage) -> str:
    """Return localized suffix when vacancy conditions cannot be summarized."""
    if language == ResponseLanguage.EN:
        return "No vacancy schedule or employment terms to summarize."
    return "Нет данных о графике или условиях занятости для обобщения."


def hh_employer_not_found(identity_name: str, language: ResponseLanguage) -> str:
    """Return localized not-found message for hh.ru employer lookup."""
    if language == ResponseLanguage.EN:
        return f"Employer not found on hh.ru for «{identity_name}»."
    return f"Работодатель не найден на hh.ru по названию «{identity_name}»."


def hh_employer_not_found_with_tried(
    identity_name: str,
    tried_queries: list[str],
    language: ResponseLanguage,
) -> str:
    """Return localized not-found message including attempted search queries."""
    tried_text: str = ", ".join(f"«{query}»" for query in tried_queries)
    if language == ResponseLanguage.EN:
        return (
            f"Employer not found on hh.ru for «{identity_name}». "
            f"Tried: {tried_text}."
        )
    return (
        f"Работодатель не найден на hh.ru по названию «{identity_name}». "
        f"Пробовали: {tried_text}."
    )


def hh_found_vacancies_message(employer_name: str, vacancy_count: int, language: ResponseLanguage) -> str:
    """Return localized success message for hh.ru vacancy lookup."""
    if language == ResponseLanguage.EN:
        return f"Found {vacancy_count} active vacancies on hh.ru for «{employer_name}»."
    return f"Найдено {vacancy_count} активных вакансий на hh.ru для «{employer_name}»."


def hh_analysis_failed_message(error: Exception, language: ResponseLanguage) -> str:
    """Return localized generic HH analysis failure message."""
    if language == ResponseLanguage.EN:
        return f"HH vacancy analysis failed: {error}"
    return f"Не удалось выполнить анализ вакансий hh.ru: {error}"
