import { useState } from "react";
import { displayHost } from "../lib/displayHost";
import { getTranslations, hhRatingDisplay, type Locale, type Translations } from "../lib/i18n";
import type { HhVacancyAnalysis } from "../types";

interface HhVacanciesPanelProps {
  hhVacancyAnalysis: HhVacancyAnalysis;
  companyName: string;
  onRetrySearch: (employerQuery: string) => Promise<void>;
  locale: Locale;
}

export function HhVacanciesPanel({
  hhVacancyAnalysis,
  companyName,
  onRetrySearch,
  locale,
}: HhVacanciesPanelProps) {
  const t: Translations = getTranslations(locale);
  const [retryQuery, setRetryQuery] = useState<string>("");
  const [isRetrying, setIsRetrying] = useState<boolean>(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  async function handleRetrySubmit(): Promise<void> {
    const trimmedQuery: string = retryQuery.trim();
    if (trimmedQuery.length === 0) {
      return;
    }
    setIsRetrying(true);
    setRetryError(null);
    try {
      await onRetrySearch(trimmedQuery);
    } catch (error: unknown) {
      const message: string = error instanceof Error ? error.message : t.hhRetryError;
      setRetryError(message);
    } finally {
      setIsRetrying(false);
    }
  }

  if (hhVacancyAnalysis.status === "error") {
    return (
      <div className="hh-vacancies-panel">
        <p className="empty-state">{hhVacancyAnalysis.message}</p>
        <p className="section-hint">{t.hhApiErrorHint}</p>
      </div>
    );
  }

  if (hhVacancyAnalysis.status === "not_found") {
    const notFoundMessage: string =
      hhVacancyAnalysis.message.trim().length > 0
        ? hhVacancyAnalysis.message
        : `Работодатель не найден на hh.ru по названию «${companyName}».`;

    return (
      <div className="hh-vacancies-panel">
        <p className="empty-state">{notFoundMessage}</p>
        <form
          className="hh-retry-form"
          onSubmit={(event) => {
            event.preventDefault();
            void handleRetrySubmit();
          }}
        >
          <label className="hh-retry-label" htmlFor="hh-retry-query">
            {t.hhRetryLabel}
          </label>
          <div className="hh-retry-row">
            <input
              id="hh-retry-query"
              className="hh-retry-input"
              type="text"
              value={retryQuery}
              placeholder={t.hhRetryPlaceholder}
              disabled={isRetrying}
              onChange={(event) => {
                setRetryQuery(event.target.value);
              }}
            />
            <button className="hh-retry-button" type="submit" disabled={isRetrying}>
              {isRetrying ? t.hhRetrySubmitting : t.hhRetrySubmit}
            </button>
          </div>
          {retryError !== null ? <p className="hh-retry-error">{retryError}</p> : null}
        </form>
      </div>
    );
  }

  const ratingValue: string | null =
    hhVacancyAnalysis.employer_rating !== null
      ? hhRatingDisplay(
          hhVacancyAnalysis.employer_rating,
          hhVacancyAnalysis.employer_rating_count,
          locale,
          t,
        )
      : null;

  return (
    <div className="hh-vacancies-panel">
      <div className="hh-summary-grid">
        {ratingValue !== null ? (
          <article
            className="hh-metric hh-metric-rating"
            aria-label={`${t.hhRatingAria}: ${ratingValue}`}
          >
            <p className="verdict-eyebrow">{t.hhRatingLabel}</p>
            <p className="hh-metric-value">{ratingValue}</p>
          </article>
        ) : null}
        <article className="hh-metric hh-metric-salary">
          <p className="verdict-eyebrow">{t.hhSalaryLabel}</p>
          <p className="hh-metric-body">{hhVacancyAnalysis.salary_summary}</p>
        </article>
        <article className="hh-metric hh-metric-conditions">
          <p className="verdict-eyebrow">{t.hhConditionsLabel}</p>
          <p className="hh-metric-body">{hhVacancyAnalysis.conditions_summary}</p>
        </article>
      </div>

      {hhVacancyAnalysis.employer_url !== null ? (
        <a
          className="hh-employer-link"
          href={hhVacancyAnalysis.employer_url}
          target="_blank"
          rel="noreferrer"
        >
          {t.hhEmployerProfile}
        </a>
      ) : null}

      <section className="hh-vacancy-list">
        <h3 className="section-title">{t.hhVacancyListTitle}</h3>
        {hhVacancyAnalysis.vacancies.length === 0 ? (
          <p className="empty-state">{t.hhVacanciesListEmpty}</p>
        ) : (
          <ul className="source-list">
            {hhVacancyAnalysis.vacancies.map((vacancy) => (
              <li key={vacancy.vacancy_id} className="source-item">
                <a
                  className="source-link"
                  href={vacancy.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <span className="source-link-title">{vacancy.title}</span>
                  <span className="source-link-host">{displayHost(vacancy.url)}</span>
                </a>
                <div className="vacancy-meta">
                  {vacancy.salary_text !== null ? (
                    <span className="badge">{vacancy.salary_text}</span>
                  ) : null}
                  {vacancy.location_text !== null ? (
                    <span className="badge">{vacancy.location_text}</span>
                  ) : null}
                  {vacancy.schedule_text !== null ? (
                    <span className="badge">{vacancy.schedule_text}</span>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
