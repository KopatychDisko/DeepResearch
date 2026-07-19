import { displayHost } from "../lib/displayHost";
import { useLanguage } from "../lib/i18n";
import type { RawFinding, SourceType } from "../types";

interface SourceLinksPanelProps {
  findings: RawFinding[];
}

function groupBySource(findings: RawFinding[]): Map<SourceType, RawFinding[]> {
  const groups: Map<SourceType, RawFinding[]> = new Map();
  for (const finding of findings) {
    const existing: RawFinding[] = groups.get(finding.source_type) ?? [];
    existing.push(finding);
    groups.set(finding.source_type, existing);
  }
  return groups;
}

export function SourceLinksPanel({ findings }: SourceLinksPanelProps) {
  const { t } = useLanguage();

  if (findings.length === 0) {
    return <p className="empty-state">{t.sourcesEmpty}</p>;
  }

  function sourceLabel(sourceType: SourceType): string {
    if (sourceType === "news") {
      return t.sourceNews;
    }
    if (sourceType === "reviews") {
      return t.sourceReviews;
    }
    return t.sourceHh;
  }

  const groups: Map<SourceType, RawFinding[]> = groupBySource(findings);

  return (
    <div className="sources-panel">
      {Array.from(groups.entries()).map(([sourceType, sourceFindings]) => (
        <section key={sourceType} className="source-group">
          <header className="source-group-header">
            <span className="source-badge">{sourceLabel(sourceType)}</span>
            <span className="source-count">
              {sourceFindings.length} {t.linksCount}
            </span>
          </header>
          <ul className="source-list">
            {sourceFindings.map((finding) => (
              <li key={`${finding.source_url}-${finding.title}`} className="source-item">
                <a
                  className="source-link"
                  href={finding.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <span className="source-link-title">{finding.title}</span>
                  <span className="source-link-host">{displayHost(finding.source_url)}</span>
                </a>
                <p className="source-snippet">{finding.snippet}</p>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
