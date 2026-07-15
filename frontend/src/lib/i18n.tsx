import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

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
  tabSources: string;
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
  phaseSupervisor: string;
  phaseStructureEvents: string;
  phaseMergeTimeline: string;
  phaseGenerateVerdict: string;
  phaseCompleted: string;
  sourceNews: string;
  sourceReviews: string;
  sourceHh: string;
  linksCount: string;
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
    tabSources: "Источники",
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
    phaseSupervisor: "Источники",
    phaseStructureEvents: "События",
    phaseMergeTimeline: "Таймлайн",
    phaseGenerateVerdict: "Вердикт",
    phaseCompleted: "Готово",
    sourceNews: "Новости",
    sourceReviews: "Отзывы",
    sourceHh: "HeadHunter",
    linksCount: "ссылок",
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
    tabSources: "Sources",
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
    phaseSupervisor: "Sources",
    phaseStructureEvents: "Events",
    phaseMergeTimeline: "Timeline",
    phaseGenerateVerdict: "Verdict",
    phaseCompleted: "Done",
    sourceNews: "News",
    sourceReviews: "Reviews",
    sourceHh: "HeadHunter",
    linksCount: "links",
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
