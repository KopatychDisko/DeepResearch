from __future__ import annotations

from agents.models import EventCategory, ResponseLanguage


def parse_response_language(value: str) -> ResponseLanguage:
    normalized: str = value.strip().lower()
    if normalized == ResponseLanguage.EN.value:
        return ResponseLanguage.EN
    if normalized == ResponseLanguage.RU.value:
        return ResponseLanguage.RU
    raise ValueError(f"Unsupported response language: {value}")


def response_language_instruction(language: ResponseLanguage) -> str:
    if language == ResponseLanguage.EN:
        return "Write all user-facing text fields in English."
    return "Write all user-facing text fields in Russian."


def event_category_label(category: EventCategory, language: ResponseLanguage) -> str:
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
    if language == ResponseLanguage.EN:
        return "Data conflict"
    return "Конфликт данных"


def insufficient_data_score_explanation(language: ResponseLanguage) -> str:
    if language == ResponseLanguage.EN:
        return "Not enough confirmed events for a confident score."
    return "Недостаточно подтверждённых событий для уверенной оценки."


def insufficient_data_summary(company_name: str, language: ResponseLanguage) -> str:
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
    if language == ResponseLanguage.EN:
        return "not provided"
    return "не указана"


def optional_description_placeholder(language: ResponseLanguage) -> str:
    if language == ResponseLanguage.EN:
        return "not provided"
    return "не указано"
