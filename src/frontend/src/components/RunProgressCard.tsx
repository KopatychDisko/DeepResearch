import { useLanguage } from "../lib/i18n";
import type { RunPhase, RunStatusResponse } from "../types";

interface RunProgressCardProps {
  status: RunStatusResponse | null;
  companyName: string;
}

const PHASE_STEPS: RunPhase[] = [
  "pending",
  "resolve_identity",
  "supervisor",
  "structure_events",
  "merge_timeline",
  "generate_verdict",
  "completed",
];

const SOURCE_ICONS: Record<string, string> = {
  news: "📰",
  reviews: "💬",
  hh: "💼",
};

function phaseLabel(phase: RunPhase, t: ReturnType<typeof useLanguage>["t"]): string {
  if (phase === "pending") return t.phasePending;
  if (phase === "resolve_identity") return t.phaseResolveIdentity;
  if (phase === "awaiting_identity") return t.phaseAwaitingIdentity;
  if (phase === "supervisor") return t.phaseSupervisor;
  if (phase === "structure_events") return t.phaseStructureEvents;
  if (phase === "merge_timeline") return t.phaseMergeTimeline;
  if (phase === "generate_verdict") return t.phaseGenerateVerdict;
  return t.phaseCompleted;
}

export function RunProgressCard({ status, companyName }: RunProgressCardProps) {
  const { t } = useLanguage();
  const currentPhase: RunPhase = status?.phase ?? "pending";
  const currentIndex: number = PHASE_STEPS.indexOf(currentPhase);
  const progressPercent: number = Math.max(
    8,
    Math.round(((currentIndex + 1) / PHASE_STEPS.length) * 100),
  );
  const displayName: string = status?.company_name || companyName || "...";
  const isAwaitingIdentity: boolean = status?.status === "awaiting_input";

  return (
    <article className="card progress-card">
      <div className="progress-header">
        {!isAwaitingIdentity ? <div className="progress-spinner" aria-hidden="true" /> : null}
        <div>
          <h2>
            {isAwaitingIdentity
              ? t.progressClarifyTitle
              : `${t.progressAnalyzing}: ${displayName}`}
          </h2>
          <p className="progress-subtitle">
            {isAwaitingIdentity ? t.progressClarifySubtitle : t.progressSubtitle}
          </p>
        </div>
      </div>

      <div className="progress-bar-track" aria-hidden="true">
        <div className="progress-bar-fill" style={{ width: `${progressPercent}%` }} />
      </div>

      <ol className="phase-steps">
        {PHASE_STEPS.filter((phase) => phase !== "completed").map((phase, index) => {
          const isDone: boolean = index < currentIndex;
          const isActive: boolean = phase === currentPhase;
          const stepClass: string = ["phase-step", isDone ? "done" : "", isActive ? "active" : ""]
            .filter(Boolean)
            .join(" ");
          return (
            <li key={phase} className={stepClass}>
              <span className="phase-step-marker">{isDone ? "✓" : index + 1}</span>
              <span className="phase-step-label">{phaseLabel(phase, t)}</span>
            </li>
          );
        })}
      </ol>

      {status !== null && !isAwaitingIdentity ? (
        <div className="progress-stats">
          <div className="stat-chip">
            <span className="stat-value">{status.findings_count}</span>
            <span className="stat-label">{t.progressFindings}</span>
          </div>
          <div className="stat-chip">
            <span className="stat-value">{status.events_count}</span>
            <span className="stat-label">{t.progressEvents}</span>
          </div>
          <div className="stat-chip sources-chip">
            {status.completed_sources.length > 0 ? (
              status.completed_sources.map((source) => (
                <span key={source} className="source-pill" title={source}>
                  {SOURCE_ICONS[source] ?? "🔗"} {source}
                </span>
              ))
            ) : (
              <span className="stat-label">{t.progressSourcesConnecting}</span>
            )}
          </div>
        </div>
      ) : null}
    </article>
  );
}
