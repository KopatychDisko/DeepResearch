import { useState } from "react";
import { useLanguage } from "../lib/i18n";
import type { RunViewModel } from "../types";
import { SourceLinksPanel } from "./SourceLinksPanel";
import { TimelineView } from "./TimelineView";
import { VerdictCard } from "./VerdictCard";

interface ResultsDashboardProps {
  result: RunViewModel;
}

type TabId = "verdict" | "timeline" | "sources";

export function ResultsDashboard({ result }: ResultsDashboardProps) {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<TabId>("verdict");
  const sourceCount: number = result.findings.length;

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

      <nav className="tab-nav" aria-label={t.reportSectionsAria}>
        <button
          type="button"
          className={activeTab === "verdict" ? "tab active" : "tab"}
          onClick={() => setActiveTab("verdict")}
        >
          {t.tabVerdict}
        </button>
        <button
          type="button"
          className={activeTab === "timeline" ? "tab active" : "tab"}
          onClick={() => setActiveTab("timeline")}
        >
          {t.tabTimeline}
        </button>
        <button
          type="button"
          className={activeTab === "sources" ? "tab active" : "tab"}
          onClick={() => setActiveTab("sources")}
        >
          {t.tabSources} ({sourceCount})
        </button>
      </nav>

      <div className="tab-content">
        {activeTab === "verdict" ? (
          <VerdictCard verdict={result.verdict} companyName={result.identity.canonical_name} />
        ) : null}
        {activeTab === "timeline" ? (
          <article className="card">
            <TimelineView timeline={result.timeline} />
          </article>
        ) : null}
        {activeTab === "sources" ? (
          <article className="card">
            <h3 className="section-title">{t.sourcesTitle}</h3>
            <p className="section-hint">{t.sourcesHint}</p>
            <SourceLinksPanel findings={result.findings} />
          </article>
        ) : null}
      </div>
    </section>
  );
}
