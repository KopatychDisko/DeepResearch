import { displayHost } from "../lib/displayHost";
import { categoryLabel, scoreLabel, useLanguage } from "../lib/i18n";
import type { EmployerVerdict, VerdictColor } from "../types";

interface VerdictCardProps {
  verdict: EmployerVerdict;
  companyName: string;
}

function ScoreRing({ score, scoreAriaLabel }: { score: number; scoreAriaLabel: string }) {
  const circumference: number = 2 * Math.PI * 42;
  const offset: number = circumference - (score / 10) * circumference;
  return (
    <div className="score-ring" aria-label={scoreAriaLabel}>
      <svg viewBox="0 0 100 100" className="score-ring-svg">
        <circle className="score-ring-bg" cx="50" cy="50" r="42" />
        <circle
          className="score-ring-fill"
          cx="50"
          cy="50"
          r="42"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="score-ring-center">
        <div className="score-ring-value">
          <span className="score-number">{score}</span>
          <span className="score-max">/10</span>
        </div>
      </div>
    </div>
  );
}

function verdictColorLabel(color: VerdictColor, t: ReturnType<typeof useLanguage>["t"]): string {
  if (color === "green") {
    return t.verdictGreen;
  }
  if (color === "yellow") {
    return t.verdictYellow;
  }
  return t.verdictRed;
}

export function VerdictCard({ verdict, companyName }: VerdictCardProps) {
  const { locale, t } = useLanguage();
  const scoreAriaLabel: string =
    locale === "en"
      ? `${t.scoreAria} ${verdict.score} out of 10`
      : `${t.scoreAria} ${verdict.score} из 10`;

  return (
    <article className={`card verdict-card ${verdict.color}`}>
      <header className="verdict-header">
        <div className="verdict-header-text">
          <p className="verdict-eyebrow">{t.verdictEyebrow}</p>
          <h2>{companyName}</h2>
          <div className="verdict-badges">
            <span className={`color-badge ${verdict.color}`}>
              {verdictColorLabel(verdict.color, t)}
            </span>
            <span className="score-badge">{scoreLabel(verdict.score, t)}</span>
          </div>
        </div>
        <ScoreRing score={verdict.score} scoreAriaLabel={scoreAriaLabel} />
      </header>

      <p className="score-explanation">{verdict.score_explanation}</p>
      <p className="verdict-summary">{verdict.summary}</p>

      {verdict.red_flags.length > 0 ? (
        <section className="insight-section red">
          <h3>🚩 {t.redFlags}</h3>
          <ul className="insight-list">
            {verdict.red_flags.map((flag) => (
              <li key={flag} className="insight-item">
                {flag}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {verdict.interesting_facts.length > 0 ? (
        <section className="insight-section highlight">
          <h3>✨ {t.interestingFacts}</h3>
          <ul className="insight-list">
            {verdict.interesting_facts.map((fact) => (
              <li key={fact} className="insight-item">
                {fact}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {verdict.risks.length > 0 ? (
        <section className="insight-section warning">
          <h3>⚠️ {t.risks}</h3>
          <ul className="insight-list">
            {verdict.risks.map((risk) => (
              <li key={risk} className="insight-item">
                {risk}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="insight-section evidence">
        <h3>{t.evidenceTitle}</h3>
        {verdict.evidence_links.length > 0 ? (
          <ul className="evidence-list">
            {verdict.evidence_links.map((link) => (
              <li
                key={`${link.event_description}-${link.date ?? "none"}`}
                className="evidence-item"
              >
                <p>{link.event_description}</p>
                <div className="timeline-meta">
                  <span className="badge">{categoryLabel(link.category, t)}</span>
                  <span className="badge">{link.confidence}</span>
                  <span>{link.date ?? t.timelineDateUnknown}</span>
                </div>
                <div className="evidence-links">
                  {link.source_urls.map((url) => (
                    <a key={url} href={url} target="_blank" rel="noreferrer">
                      {displayHost(url)}
                    </a>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty-state">{t.evidenceEmpty}</p>
        )}
      </section>
    </article>
  );
}
