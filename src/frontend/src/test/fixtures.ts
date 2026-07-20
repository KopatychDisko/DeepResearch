import type { EmployerVerdict, HhVacancyAnalysis, RunViewModel } from "../types";

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

export const mockHhVacancyAnalysisFound: HhVacancyAnalysis = {
  status: "found",
  message: "Found 2 active vacancies on hh.ru for «Acme Corporation».",
  search_queries_tried: ["Acme Corporation"],
  matched_search_query: "Acme Corporation",
  employer_name: "Acme Corporation",
  employer_url: "https://hh.ru/employer/12345",
  employer_rating: 4.2,
  employer_rating_count: 128,
  salary_summary: "150 000 – 220 000 ₽ typical range for engineering roles.",
  conditions_summary: "Hybrid and remote schedules common; full-time employment.",
  vacancies: [
    {
      vacancy_id: "vac-001",
      title: "Senior Backend Engineer",
      url: "https://hh.ru/vacancy/100001",
      salary_text: "180 000 – 250 000 ₽",
      location_text: "Moscow",
      schedule_text: "full-time, remote",
      published_at: "2026-07-01",
    },
    {
      vacancy_id: "vac-002",
      title: "Product Manager",
      url: "https://hh.ru/vacancy/100002",
      salary_text: "200 000 – 280 000 ₽",
      location_text: "Saint Petersburg",
      schedule_text: "full-time, hybrid",
      published_at: "2026-07-10",
    },
  ],
};

export const mockHhVacancyAnalysisNotFound: HhVacancyAnalysis = {
  status: "not_found",
  message: 'Employer not found on hh.ru for "Acme Corporation".',
  search_queries_tried: ["Acme Corporation", "Acme"],
  matched_search_query: null,
  employer_name: null,
  employer_url: null,
  employer_rating: null,
  employer_rating_count: null,
  salary_summary: "",
  conditions_summary: "",
  vacancies: [],
};

export const mockRunViewModelWithHh: RunViewModel = {
  ...mockRunViewModel,
  hhVacancyAnalysis: mockHhVacancyAnalysisFound,
};

export const mockHhNotFoundViewModel: RunViewModel = {
  ...mockRunViewModel,
  hhVacancyAnalysis: mockHhVacancyAnalysisNotFound,
};
