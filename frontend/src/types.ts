export type VerdictColor = "green" | "yellow" | "red";

export type Confidence = "high" | "medium" | "low";

export type SourceType = "news" | "reviews" | "hh";

export type RunPhase =
  | "pending"
  | "resolve_identity"
  | "awaiting_identity"
  | "supervisor"
  | "structure_events"
  | "merge_timeline"
  | "generate_verdict"
  | "completed";

export type RunLifecycleStatus =
  | "running"
  | "awaiting_input"
  | "completed"
  | "failed"
  | "interrupted";

export interface CompanyCandidate {
  candidate_id: string;
  name: string;
  description: string;
  website_url: string | null;
  confidence: Confidence;
}

export type EventCategory =
  | "funding"
  | "leadership"
  | "layoffs"
  | "scandal"
  | "product"
  | "review_signal";

export interface CompanyIdentity {
  query_name: string;
  canonical_name: string;
  normalized_name: string;
  company_url: string | null;
  profile_summary: string | null;
  user_description: string | null;
}

export interface CanonicalTimelineEvent {
  date: string | null;
  category: EventCategory;
  description: string;
  source_urls: string[];
  confidence: Confidence;
  has_date_conflict: boolean;
}

export interface TimelineConflict {
  category: EventCategory;
  message: string;
  source_urls: string[];
  dates: string[];
}

export interface CanonicalTimeline {
  events: CanonicalTimelineEvent[];
  conflicts: TimelineConflict[];
}

export interface VerdictEvidenceLink {
  event_description: string;
  category: EventCategory;
  confidence: Confidence;
  source_urls: string[];
  date: string | null;
}

export interface EmployerVerdict {
  color: VerdictColor;
  score: number;
  score_explanation: string;
  summary: string;
  risks: string[];
  red_flags: string[];
  interesting_facts: string[];
  evidence_links: VerdictEvidenceLink[];
}

export interface RetrievalMetadata {
  fetched_at: string;
  source_label: string;
  note: string;
}

export interface RawFinding {
  source_type: SourceType;
  source_url: string;
  title: string;
  snippet: string;
  metadata: RetrievalMetadata;
}

export interface ResearchRunResult {
  identity: CompanyIdentity;
  findings: RawFinding[];
  timeline: CanonicalTimeline;
  verdict: EmployerVerdict;
}

export interface RunStatusResponse {
  run_id: string;
  created_at: string;
  status: RunLifecycleStatus;
  phase: RunPhase;
  company_name: string;
  completed_sources: SourceType[];
  findings_count: number;
  events_count: number;
  iteration_count: number;
  error_message: string | null;
  identity_candidates: CompanyCandidate[];
  result: ResearchRunResult | null;
}

export interface RunStartResponse {
  run_id: string;
  created_at: string;
  status: RunLifecycleStatus;
  phase: RunPhase;
  message: string;
}

export interface RunViewModel {
  runId: string;
  identity: CompanyIdentity;
  findings: RawFinding[];
  timeline: CanonicalTimeline;
  verdict: EmployerVerdict;
}
