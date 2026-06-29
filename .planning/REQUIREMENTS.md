# Requirements: Employer Due Diligence Agent

**Defined:** 2026-06-29
**Core Value:** Before every interview, you can run one query on a company name and get a trustworthy, source-backed timeline and verdict.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Ingestion & Identity

- [ ] **INGEST-01**: User can submit a company name and start an on-demand due diligence run
- [ ] **INGEST-02**: System resolves company identity anchors before cross-source aggregation
- [ ] **INGEST-03**: System collects findings from open Russian-language sources (news, reviews, hh/job-board footprint)
- [ ] **INGEST-04**: Each raw finding stores source URL and retrieval metadata for traceability

### Event Extraction

- [ ] **EVENT-01**: System extracts timeline events into structured schema (`date`, `category`, `description`, `source_url`, `confidence`)
- [ ] **EVENT-02**: System supports event categories `funding`, `leadership`, `layoffs`, `scandal`, `product`, `review_signal`
- [ ] **EVENT-03**: System avoids fabricated facts by requiring source-backed evidence for extracted events
- [ ] **EVENT-04**: System chunks long source content before structured extraction to preserve quality and cost control

### Merge & Timeline

- [ ] **MERGE-01**: System semantically deduplicates equivalent events from different sources into one canonical event
- [ ] **MERGE-02**: System preserves multiple source URLs for merged canonical events
- [ ] **MERGE-03**: System sorts timeline events by date and handles unknown dates without breaking chronology output
- [ ] **MERGE-04**: System surfaces conflicts when high-impact sources disagree on key facts

### Verdict & UX

- [ ] **VERDICT-01**: User can view verdict color (`green` / `yellow` / `red`) derived from canonical timeline events
- [ ] **VERDICT-02**: User can view dedicated verdict sections: risks, interview questions, and red flags
- [ ] **VERDICT-03**: User can inspect confidence and source links behind verdict-relevant events
- [ ] **UI-01**: User can view timeline visualization and verdict card in React UI

### Reliability & Observability

- [ ] **OBS-01**: System checkpointing persists long-running graph execution and supports progress/status inspection
- [ ] **OBS-02**: Langfuse traces each source-specific researcher path separately
- [ ] **EVAL-01**: Project includes DeepEval dataset and tests for recall, date/fact accuracy, and dedup quality (non-blocking for v1 release)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Scale & Productization

- **CACHE-01**: System caches completed company reports in Supabase/Postgres and reuses fresh results when possible
- **MON-01**: System supports optional scheduled monitoring mode for tracked companies
- **GLOBAL-01**: System expands beyond Russian-language sources to multilingual coverage
- **API-01**: System supports multi-user/public SaaS usage model

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Closed/login-only source parsing (e.g., LinkedIn) | v1 uses open web sources only |
| Real-time continuous monitoring | on-demand workflow is the v1 target |
| International/non-RU source-first scope | v1 focus is Russian-language interview context |
| Opaque single-score employer ranking | conflicts with evidence transparency and explainability |
| Fully autonomous pass/fail employer recommendation | overstates certainty and increases risk; product is decision support |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 1 | Pending |
| INGEST-02 | Phase 1 | Pending |
| INGEST-03 | Phase 1 | Pending |
| INGEST-04 | Phase 1 | Pending |
| EVENT-01 | Phase 2 | Pending |
| EVENT-02 | Phase 2 | Pending |
| EVENT-03 | Phase 2 | Pending |
| EVENT-04 | Phase 2 | Pending |
| MERGE-01 | Phase 3 | Pending |
| MERGE-02 | Phase 3 | Pending |
| MERGE-03 | Phase 3 | Pending |
| MERGE-04 | Phase 3 | Pending |
| VERDICT-01 | Phase 4 | Pending |
| VERDICT-02 | Phase 4 | Pending |
| VERDICT-03 | Phase 4 | Pending |
| UI-01 | Phase 4 | Pending |
| OBS-01 | Phase 5 | Pending |
| OBS-02 | Phase 5 | Pending |
| EVAL-01 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-29*
*Last updated: 2026-06-29 after roadmap mapping*
