import { useLanguage } from "../lib/i18n";
import type { RunViewModel } from "../types";
import { HhVacanciesPanel } from "./HhVacanciesPanel";
import { SourceLinksPanel } from "./SourceLinksPanel";
import { VerdictCard } from "./VerdictCard";

interface ResultsDashboardProps {
  result: RunViewModel;
}

export function ResultsDashboard({ result }: ResultsDashboardProps) {
  const { t } = useLanguage();
  const sourceCount: number = result.findings.length;
  const hhVacancyCount: number = result.hhVacancyAnalysis?.vacancies.length ?? 0;

  return (
    <section className="results-dashboard">
      <header className="results-header">
        <div>
          <p className="results-eyebrow">{t.reportReady}</p>
          <h2>{result.identity.canonical_name}</h2>
        </div>
        <div className="results-meta">
          <span className="meta-pill">
            {sourceCount} {t.sourcesCount}
          </span>
        </div>
      </header>

      <VerdictCard verdict={result.verdict} companyName={result.identity.canonical_name} />

      {result.hhVacancyAnalysis !== undefined ? (
        <details className="collapsible-section card">
          <summary className="collapsible-summary">
            {t.hhVacanciesTitle} ({hhVacancyCount})
          </summary>
          <p className="section-hint">{t.hhVacanciesHint}</p>
          <HhVacanciesPanel
            hhVacancyAnalysis={result.hhVacancyAnalysis}
            companyName={result.identity.canonical_name}
          />
        </details>
      ) : null}

      <details className="collapsible-section card">
        <summary className="collapsible-summary">
          {t.tabSources} ({sourceCount})
        </summary>
        <p className="section-hint">{t.sourcesHint}</p>
        <SourceLinksPanel findings={result.findings} />
      </details>
    </section>
  );
}
