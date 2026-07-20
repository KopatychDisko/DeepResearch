import { displayHost } from "../lib/displayHost";
import { hhNotFoundMessage, hhRatingDisplay, useLanguage } from "../lib/i18n";
import type { HhVacancyAnalysis } from "../types";

interface HhVacanciesPanelProps {
  hhVacancyAnalysis: HhVacancyAnalysis;
  companyName: string;
}

export function HhVacanciesPanel({
  hhVacancyAnalysis,
  companyName,
}: HhVacanciesPanelProps) {
  const { locale, t } = useLanguage();

  if (hhVacancyAnalysis.status === "not_found") {
    return (
      <div className="hh-vacancies-panel">
        <p className="empty-state">{hhNotFoundMessage(companyName, t)}</p>
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
            className="hh-metric"
            aria-label={`${t.hhRatingAria}: ${ratingValue}`}
          >
            <p className="verdict-eyebrow">{t.hhRatingLabel}</p>
            <p className="hh-metric-value">{ratingValue}</p>
          </article>
        ) : null}
        <article className="hh-metric">
          <p className="verdict-eyebrow">{t.hhSalaryLabel}</p>
          <p className="hh-metric-value">{hhVacancyAnalysis.salary_summary}</p>
        </article>
        <article className="hh-metric">
          <p className="verdict-eyebrow">{t.hhConditionsLabel}</p>
          <p className="hh-metric-value">{hhVacancyAnalysis.conditions_summary}</p>
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
