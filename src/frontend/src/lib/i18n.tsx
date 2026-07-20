import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { EventCategory } from "../types";

export type Locale = "ru" | "en";

const STORAGE_KEY = "employer-dd-locale";

export interface Translations {
  headerBadge: string;
  headerTitle: string;
  headerSubtitle: string;
  companyNamePlaceholder: string;
  companyUrlPlaceholder: string;
  companyDescriptionPlaceholder: string;
  submit: string;
  submitting: string;
  errorRunFailed: string;
  errorNoResult: string;
  errorAnalysisFailed: string;
  errorNoActiveRun: string;
  errorConfirmFailed: string;
  progressAnalyzing: string;
  progressSubtitle: string;
  progressClarifyTitle: string;
  progressClarifySubtitle: string;
  progressFindings: string;
  progressEvents: string;
  progressSourcesConnecting: string;
  identityPickerTitle: string;
  identitySelect: string;
  identitySelecting: string;
  confidenceHigh: string;
  confidenceMedium: string;
  confidenceLow: string;
  reportReady: string;
  sourcesCount: string;
  tabVerdict: string;
  tabTimeline: string;
  tabSources: string;
  reportSectionsAria: string;
  sourcesTitle: string;
  sourcesHint: string;
  sourcesEmpty: string;
  verdictEyebrow: string;
  scoreAria: string;
  redFlags: string;
  interestingFacts: string;
  risks: string;
  verdictGreen: string;
  verdictYellow: string;
  verdictRed: string;
  scoreExcellent: string;
  scorePositive: string;
  scoreCheck: string;
  scoreConcerns: string;
  scoreHighRisk: string;
  phasePending: string;
  phaseResolveIdentity: string;
  phaseAwaitingIdentity: string;
  phaseAnalyzeHhVacancies: string;
  phaseSupervisor: string;
  phaseStructureEvents: string;
  phaseMergeTimeline: string;
  phaseGenerateVerdict: string;
  phaseCompleted: string;
  sourceNews: string;
  sourceReviews: string;
  sourceHh: string;
  linksCount: string;
  evidenceTitle: string;
  evidenceEmpty: string;
  timelineDateUnknown: string;
  timelineEmpty: string;
  timelineDateConflict: string;
  timelineConflictsHeading: string;
  categoryFunding: string;
  categoryLeadership: string;
  categoryLayoffs: string;
  categoryScandal: string;
  categoryProduct: string;
  categoryReviewSignal: string;
  hhVacanciesTitle: string;
  hhVacanciesHint: string;
  hhVacanciesNotFound: string;
  hhVacancyListTitle: string;
  hhVacanciesListEmpty: string;
  hhRatingLabel: string;
  hhSalaryLabel: string;
  hhConditionsLabel: string;
  hhEmployerProfile: string;
  hhRatingAria: string;
  hhVacanciesCount: string;
  hhRetryLabel: string;
  hhRetryPlaceholder: string;
  hhRetrySubmit: string;
  hhRetrySubmitting: string;
  hhRetryError: string;
  hhApiErrorHint: string;
  languageLockedHint: string;
}

const translations: Record<Locale, Translations> = {
  ru: {
    headerBadge: "Employer DD",
    headerTitle: "Проверка работодателя",
    headerSubtitle:
      "Сначала проверяем, что компания существует, затем формируем вердикт и список источников. Ссылка и описание помогают выбрать нужную организацию.",
    companyNamePlaceholder: "Название компании",
    companyUrlPlaceholder: "Ссылка на сайт компании (необязательно)",
    companyDescriptionPlaceholder:
      "Описание компании (необязательно): чем занимается, город, продукт — поможет найти нужную организацию",
    submit: "Проверить",
    submitting: "Анализ...",
    errorRunFailed: "Анализ завершился с ошибкой.",
    errorNoResult: "Анализ завершён, но результат отсутствует.",
    errorAnalysisFailed: "Не удалось выполнить анализ компании.",
    errorNoActiveRun: "Не удалось определить активный запуск.",
    errorConfirmFailed: "Не удалось подтвердить компанию.",
    progressAnalyzing: "Анализируем",
    progressSubtitle: "Проверяем компанию в открытых источниках и формируем отчёт…",
    progressClarifyTitle: "Уточните компанию",
    progressClarifySubtitle: "Найдено несколько совпадений — выберите нужную организацию ниже.",
    progressFindings: "находок",
    progressEvents: "событий",
    progressSourcesConnecting: "источники подключаются…",
    identityPickerTitle: "Какую компанию вы имели в виду?",
    identitySelect: "Выбрать",
    identitySelecting: "Запуск…",
    confidenceHigh: "высокая уверенность",
    confidenceMedium: "средняя уверенность",
    confidenceLow: "низкая уверенность",
    reportReady: "Отчёт готов",
    sourcesCount: "источников",
    tabVerdict: "Вердикт",
    tabTimeline: "Таймлайн",
    tabSources: "Источники",
    reportSectionsAria: "Разделы отчёта",
    sourcesTitle: "Ссылки, использованные в отчёте",
    sourcesHint:
      "Все материалы, которые агент нашёл в открытых источниках перед формированием вердикта.",
    sourcesEmpty: "Источники не собраны.",
    verdictEyebrow: "Вердикт по работодателю",
    scoreAria: "Оценка",
    redFlags: "Красные флаги",
    interestingFacts: "Интересные факты",
    risks: "Риски",
    verdictGreen: "Низкий риск",
    verdictYellow: "Смешанные сигналы",
    verdictRed: "Высокий риск",
    scoreExcellent: "Отличный выбор",
    scorePositive: "Скорее позитивно",
    scoreCheck: "Нужна проверка",
    scoreConcerns: "Есть опасения",
    scoreHighRisk: "Высокий риск",
    phasePending: "Подготовка",
    phaseResolveIdentity: "Проверка компании",
    phaseAwaitingIdentity: "Выбор компании",
    phaseAnalyzeHhVacancies: "Вакансии hh.ru",
    phaseSupervisor: "Источники",
    phaseStructureEvents: "События",
    phaseMergeTimeline: "Таймлайн",
    phaseGenerateVerdict: "Вердикт",
    phaseCompleted: "Готово",
    sourceNews: "Новости",
    sourceReviews: "Отзывы",
    sourceHh: "HeadHunter",
    linksCount: "ссылок",
    evidenceTitle: "Источники вердикта",
    evidenceEmpty: "Нет привязанных источников для вердикта.",
    timelineDateUnknown: "дата неизвестна",
    timelineEmpty: "События не найдены.",
    timelineDateConflict: "конфликт дат",
    timelineConflictsHeading: "Конфликты в данных",
    categoryFunding: "Финансы",
    categoryLeadership: "Руководство",
    categoryLayoffs: "Сокращения",
    categoryScandal: "Скандал",
    categoryProduct: "Продукт",
    categoryReviewSignal: "Отзывы",
    hhVacanciesTitle: "Вакансии на hh.ru",
    hhVacanciesHint:
      "Оценка работодателя, зарплаты и условия по открытым вакансиям на hh.ru. Не влияет на общий вердикт.",
    hhVacanciesNotFound: "Работодатель не найден на hh.ru по названию «{companyName}».",
    hhVacancyListTitle: "Открытые вакансии",
    hhVacanciesListEmpty: "Активных вакансий не найдено.",
    hhRatingLabel: "Рейтинг на hh.ru",
    hhSalaryLabel: "Зарплаты",
    hhConditionsLabel: "Условия работы",
    hhEmployerProfile: "Профиль работодателя на hh.ru",
    hhRatingAria: "Рейтинг работодателя",
    hhVacanciesCount: "вакансий",
    hhRetryLabel: "Поискать на hh.ru по другому названию",
    hhRetryPlaceholder: "Например: Сбер или Сбербанк",
    hhRetrySubmit: "Найти на hh.ru",
    hhRetrySubmitting: "Ищем...",
    hhRetryError: "Не удалось повторить поиск на hh.ru.",
    hhApiErrorHint: "Зарегистрируйте приложение на dev.hh.ru и задайте HH_API_USER_AGENT в .env.",
    languageLockedHint: "Язык фиксируется на время анализа",
  },
  en: {
    headerBadge: "Employer DD",
    headerTitle: "Employer check",
    headerSubtitle:
      "We verify the company exists, then produce a verdict and source list. A website URL and short description help pick the right organization.",
    companyNamePlaceholder: "Company name",
    companyUrlPlaceholder: "Company website URL (optional)",
    companyDescriptionPlaceholder:
      "Company description (optional): industry, city, product — helps find the right organization",
    submit: "Analyze",
    submitting: "Analyzing...",
    errorRunFailed: "The analysis failed.",
    errorNoResult: "The analysis completed but no result was returned.",
    errorAnalysisFailed: "Could not run the company analysis.",
    errorNoActiveRun: "Could not determine the active run.",
    errorConfirmFailed: "Could not confirm the company.",
    progressAnalyzing: "Analyzing",
    progressSubtitle: "Checking open sources and building the report…",
    progressClarifyTitle: "Clarify the company",
    progressClarifySubtitle: "Multiple matches found — choose the right organization below.",
    progressFindings: "findings",
    progressEvents: "events",
    progressSourcesConnecting: "connecting sources…",
    identityPickerTitle: "Which company did you mean?",
    identitySelect: "Select",
    identitySelecting: "Starting…",
    confidenceHigh: "high confidence",
    confidenceMedium: "medium confidence",
    confidenceLow: "low confidence",
    reportReady: "Report ready",
    sourcesCount: "sources",
    tabVerdict: "Verdict",
    tabTimeline: "Timeline",
    tabSources: "Sources",
    reportSectionsAria: "Report sections",
    sourcesTitle: "Links used in the report",
    sourcesHint: "All materials the agent found in open sources before forming the verdict.",
    sourcesEmpty: "No sources collected.",
    verdictEyebrow: "Employer verdict",
    scoreAria: "Score",
    redFlags: "Red flags",
    interestingFacts: "Interesting facts",
    risks: "Risks",
    verdictGreen: "Low risk",
    verdictYellow: "Mixed signals",
    verdictRed: "High risk",
    scoreExcellent: "Strong choice",
    scorePositive: "Mostly positive",
    scoreCheck: "Needs review",
    scoreConcerns: "Some concerns",
    scoreHighRisk: "High risk",
    phasePending: "Setup",
    phaseResolveIdentity: "Company check",
    phaseAwaitingIdentity: "Choose company",
    phaseAnalyzeHhVacancies: "HH vacancies",
    phaseSupervisor: "Sources",
    phaseStructureEvents: "Events",
    phaseMergeTimeline: "Timeline",
    phaseGenerateVerdict: "Verdict",
    phaseCompleted: "Done",
    sourceNews: "News",
    sourceReviews: "Reviews",
    sourceHh: "HeadHunter",
    linksCount: "links",
    evidenceTitle: "Verdict evidence",
    evidenceEmpty: "No linked sources for this verdict.",
    timelineDateUnknown: "date unknown",
    timelineEmpty: "No events found.",
    timelineDateConflict: "date conflict",
    timelineConflictsHeading: "Data conflicts",
    categoryFunding: "Funding",
    categoryLeadership: "Leadership",
    categoryLayoffs: "Layoffs",
    categoryScandal: "Scandal",
    categoryProduct: "Product",
    categoryReviewSignal: "Reviews",
    hhVacanciesTitle: "HH vacancies",
    hhVacanciesHint:
      "Employer rating, salary, and conditions from open hh.ru vacancies. Does not affect the overall verdict.",
    hhVacanciesNotFound: 'Employer not found on hh.ru for "{companyName}".',
    hhVacancyListTitle: "Open vacancies",
    hhVacanciesListEmpty: "No active vacancies found.",
    hhRatingLabel: "hh.ru rating",
    hhSalaryLabel: "Salaries",
    hhConditionsLabel: "Working conditions",
    hhEmployerProfile: "Employer profile on hh.ru",
    hhRatingAria: "Employer rating",
    hhVacanciesCount: "vacancies",
    hhRetryLabel: "Search hh.ru with a different employer name",
    hhRetryPlaceholder: "For example: Sber or Sberbank",
    hhRetrySubmit: "Search on hh.ru",
    hhRetrySubmitting: "Searching...",
    hhRetryError: "Failed to retry hh.ru search.",
    hhApiErrorHint: "Register an app at dev.hh.ru and set HH_API_USER_AGENT in .env.",
    languageLockedHint: "Language is locked while analysis is in progress",
  },
};

interface LanguageContextValue {
  locale: Locale;
  t: Translations;
  setLocale: (locale: Locale) => void;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function readStoredLocale(): Locale {
  const stored: string | null = localStorage.getItem(STORAGE_KEY);
  if (stored === "en") {
    return "en";
  }
  return "ru";
}

export function getTranslations(locale: Locale): Translations {
  return translations[locale];
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(readStoredLocale);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = (nextLocale: Locale): void => {
    setLocaleState(nextLocale);
    localStorage.setItem(STORAGE_KEY, nextLocale);
    document.documentElement.lang = nextLocale;
  };

  const value: LanguageContextValue = useMemo(
    () => ({
      locale,
      t: translations[locale],
      setLocale,
    }),
    [locale],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const context: LanguageContextValue | null = useContext(LanguageContext);
  if (context === null) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return context;
}

export function scoreLabel(score: number, t: Translations): string {
  if (score >= 9) {
    return t.scoreExcellent;
  }
  if (score >= 7) {
    return t.scorePositive;
  }
  if (score >= 5) {
    return t.scoreCheck;
  }
  if (score >= 3) {
    return t.scoreConcerns;
  }
  return t.scoreHighRisk;
}

export function categoryLabel(category: EventCategory, t: Translations): string {
  if (category === "funding") {
    return t.categoryFunding;
  }
  if (category === "leadership") {
    return t.categoryLeadership;
  }
  if (category === "layoffs") {
    return t.categoryLayoffs;
  }
  if (category === "scandal") {
    return t.categoryScandal;
  }
  if (category === "product") {
    return t.categoryProduct;
  }
  return t.categoryReviewSignal;
}

export function hhNotFoundMessage(companyName: string, t: Translations): string {
  return t.hhVacanciesNotFound.replace("{companyName}", companyName);
}

export function hhRatingDisplay(
  rating: number,
  count: number | null,
  locale: Locale,
  _t: Translations,
): string {
  if (count !== null && count > 0) {
    return locale === "en"
      ? `${rating} of 5 (${count} reviews)`
      : `${rating} из 5 (${count} отзывов)`;
  }
  return locale === "en" ? `${rating} of 5` : `${rating} из 5`;
}
