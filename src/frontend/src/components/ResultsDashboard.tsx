import { getTranslations, useLanguage, type Locale, type Translations } from "../lib/i18n";
import type { RunViewModel } from "../types";
import { HhVacanciesPanel } from "./HhVacanciesPanel";
import { SourceLinksPanel } from "./SourceLinksPanel";
import { VerdictCard } from "./VerdictCard";

interface ResultsDashboardProps {
  result: RunViewModel;
  onRetryHhSearch: (employerQuery: string) => Promise<void>;
  contentLocale: Locale;
}

export function ResultsDashboard({
  result,
  onRetryHhSearch,
  contentLocale,
}: ResultsDashboardProps) {
  const { t: globalT } = useLanguage();
  const t: Translations = getTranslations(contentLocale);
  const sourceCount: number = result.findings.length;
  const hhVacancyCount: number = result.hhVacancyAnalysis?.vacancies.length ?? 0;

  return (
    <section className="results-dashboard">
      <header className="results-header">
        <div>
          <p className="results-eyebrow">{globalT.reportReady}</p>
          <h2>{result.identity.canonical_name}</h2>
        </div>
        <div className="results-meta">
          <span className="meta-pill">
            {sourceCount} {globalT.sourcesCount}
          </span>
        </div>
      </header>

      <VerdictCard verdict={result.verdict} companyName={result.identity.canonical_name} />

      {result.hhVacancyAnalysis !== undefined ? (
        <details className="collapsible-section card hh-section" open>
          <summary className="collapsible-summary">
            {t.hhVacanciesTitle} ({hhVacancyCount})
          </summary>
          <p className="section-hint">{t.hhVacanciesHint}</p>
          <HhVacanciesPanel
            hhVacancyAnalysis={result.hhVacancyAnalysis}
            companyName={result.identity.canonical_name}
            onRetrySearch={onRetryHhSearch}
            locale={contentLocale}
          />
        </details>
      ) : null}

      <details className="collapsible-section card">
        <summary className="collapsible-summary">
          {globalT.tabSources} ({sourceCount})
        </summary>
        <p className="section-hint">{globalT.sourcesHint}</p>
        <SourceLinksPanel findings={result.findings} />
      </details>
    </section>
  );
}
