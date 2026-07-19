import type { EmployerVerdict, RunViewModel } from "../types";

export const mockVerdict: EmployerVerdict = {
  color: "yellow",
  score: 6,
  score_explanation: "Mixed signals from recent layoffs and steady product shipping.",
  summary: "Overall mixed employer signals with both risks and positives.",
  risks: ["High attrition reported on review sites"],
  red_flags: ["Multiple layoff announcements in the last 18 months"],
  interesting_facts: ["Raised a Series B from a well-known fund"],
  evidence_links: [
    {
      event_description: "Company announced a 10% workforce reduction",
      category: "layoffs",
      confidence: "high",
      source_urls: ["https://example.com/news/layoffs-2024"],
      date: "2024-03-15",
    },
  ],
};

export const mockRunViewModel: RunViewModel = {
  runId: "run-fixture-001",
  identity: {
    query_name: "Acme Corp",
    canonical_name: "Acme Corporation",
    normalized_name: "acme corporation",
    company_url: "https://acme.example.com",
    profile_summary: "B2B SaaS company",
    user_description: null,
  },
  findings: [
    {
      source_type: "news",
      source_url: "https://example.com/news/layoffs-2024",
      title: "Acme cuts 10% of staff",
      snippet: "The company confirmed a workforce reduction.",
      metadata: {
        fetched_at: "2024-03-16T12:00:00Z",
        source_label: "Example News",
        note: "fixture",
      },
    },
  ],
  timeline: {
    events: [
      {
        date: "2024-03-15",
        category: "layoffs",
        description: "Company announced a 10% workforce reduction",
        source_urls: ["https://example.com/news/layoffs-2024"],
        confidence: "high",
        has_date_conflict: false,
      },
    ],
    conflicts: [],
  },
  verdict: mockVerdict,
};
