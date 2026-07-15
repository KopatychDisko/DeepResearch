import { useLanguage } from "../lib/i18n";
import type { CompanyCandidate } from "../types";

interface IdentityPickerProps {
  candidates: CompanyCandidate[];
  message: string | null;
  isSubmitting: boolean;
  onSelect: (candidateId: string) => void;
}

export function IdentityPicker({
  candidates,
  message,
  isSubmitting,
  onSelect,
}: IdentityPickerProps) {
  const { t } = useLanguage();

  function confidenceLabel(confidence: CompanyCandidate["confidence"]): string {
    if (confidence === "high") {
      return t.confidenceHigh;
    }
    if (confidence === "medium") {
      return t.confidenceMedium;
    }
    return t.confidenceLow;
  }

  return (
    <article className="card identity-picker">
      <h2>{t.identityPickerTitle}</h2>
      {message !== null ? <p className="section-hint">{message}</p> : null}
      <ul className="candidate-list">
        {candidates.map((candidate) => (
          <li key={candidate.candidate_id} className="candidate-item">
            <div className="candidate-content">
              <div className="candidate-header">
                <h3>{candidate.name}</h3>
                <span className="confidence-badge">
                  {confidenceLabel(candidate.confidence)}
                </span>
              </div>
              <p className="candidate-description">{candidate.description}</p>
              {candidate.website_url !== null ? (
                <a
                  className="candidate-link"
                  href={candidate.website_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {candidate.website_url}
                </a>
              ) : null}
            </div>
            <button
              type="button"
              className="candidate-select-btn"
              disabled={isSubmitting}
              onClick={() => onSelect(candidate.candidate_id)}
            >
              {isSubmitting ? t.identitySelecting : t.identitySelect}
            </button>
          </li>
        ))}
      </ul>
    </article>
  );
}
