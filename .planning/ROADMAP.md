# Roadmap: Employer Due Diligence Agent

## Overview

This roadmap delivers an evidence-first employer due diligence copilot in vertical phases: ingest trustworthy Russian-language source findings, normalize them into source-backed events, merge into a canonical timeline, render interview-ready verdict UX, and harden reliability/observability for repeatable use.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Identity & Ingestion Foundation** - User can start a run and retrieve traceable RU-source findings for one company.
- [ ] **Phase 2: Event Extraction & Evidence Grounding** - Raw findings become structured, source-backed timeline events.
- [ ] **Phase 3: Canonical Merge & Timeline Integrity** - Equivalent cross-source events are merged into a conflict-aware chronological timeline.
- [ ] **Phase 4: Verdict & Interview UX** - User sees actionable verdict and can inspect evidence in the React interface.
- [ ] **Phase 5: Reliability, Tracing & Eval Baseline** - Long runs are resilient, traceable per source path, and regression-tested.

## Phase Details

### Phase 1: Identity & Ingestion Foundation
**Goal**: User can submit a company and receive traceable raw findings from relevant open RU sources for that run.
**Depends on**: Nothing (first phase)
**Requirements**: INGEST-01, INGEST-02, INGEST-03, INGEST-04
**Success Criteria** (what must be TRUE):
  1. User can submit a company name and see a due diligence run start successfully.
  2. Run output consistently ties findings to one resolved company identity record before cross-source aggregation.
  3. User-visible run results include findings from supported open RU source types (news, reviews, HH/job-board footprint) when available.
  4. Every finding shown in run artifacts includes source URL and retrieval metadata for auditability.
**Plans**: TBD
**Mode:** mvp

### Phase 2: Event Extraction & Evidence Grounding
**Goal**: Retrieved source content is transformed into typed, evidence-backed timeline events with defined categories.
**Depends on**: Phase 1
**Requirements**: EVENT-01, EVENT-02, EVENT-03, EVENT-04
**Success Criteria** (what must be TRUE):
  1. User-facing timeline JSON contains events with `date`, `category`, `description`, `source_url`, and `confidence`.
  2. Extracted events only use the supported categories: funding, leadership, layoffs, scandal, product, review_signal.
  3. Events lacking source-backed support are excluded from extracted output rather than presented as facts.
  4. Long source documents are chunked before extraction and still produce coherent structured events.
**Plans**: TBD
**Mode:** mvp

### Phase 3: Canonical Merge & Timeline Integrity
**Goal**: User gets one canonical timeline that removes duplicate stories, preserves provenance, and surfaces meaningful conflicts.
**Depends on**: Phase 2
**Requirements**: MERGE-01, MERGE-02, MERGE-03, MERGE-04
**Success Criteria** (what must be TRUE):
  1. Equivalent events reported by multiple sources appear once in the canonical timeline.
  2. Canonical events preserve multiple supporting source URLs when merged from different findings.
  3. Timeline output is chronologically ordered by date and remains usable when some events have unknown dates.
  4. User can identify flagged high-impact fact conflicts when sources disagree.
**Plans**: TBD
**Mode:** mvp

### Phase 4: Verdict & Interview UX
**Goal**: User can review a clear verdict and interview prep guidance, with transparent links from verdict to supporting events.
**Depends on**: Phase 3
**Requirements**: VERDICT-01, VERDICT-02, VERDICT-03, UI-01
**Success Criteria** (what must be TRUE):
  1. User can view a verdict color (`green`, `yellow`, or `red`) generated from canonical timeline events.
  2. User can see dedicated verdict sections for risks, interview questions, and red flags.
  3. User can inspect confidence and source links for verdict-relevant events directly from the product flow.
  4. User can view timeline visualization and verdict card together in the React UI.
**Plans**: TBD
**Mode:** mvp
**UI hint**: yes

### Phase 5: Reliability, Tracing & Eval Baseline
**Goal**: User can run long due diligence jobs reliably while the system captures per-source execution traces and quality regression checks.
**Depends on**: Phase 4
**Requirements**: OBS-01, OBS-02, EVAL-01
**Success Criteria** (what must be TRUE):
  1. Long-running runs can resume from checkpoints and expose progress/status instead of restarting from scratch.
  2. Observability records show distinct traces for each source-specific researcher path.
  3. Project test assets include DeepEval dataset/tests for recall, date/fact accuracy, and dedup quality, available for non-blocking v1 checks.
**Plans**: TBD
**Mode:** mvp

## Progress

**Execution Order:**
Phases execute in numeric order: 2 -> 2.1 -> 2.2 -> 3 -> 3.1 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Identity & Ingestion Foundation | 0/TBD | Not started | - |
| 2. Event Extraction & Evidence Grounding | 0/TBD | Not started | - |
| 3. Canonical Merge & Timeline Integrity | 0/TBD | Not started | - |
| 4. Verdict & Interview UX | 0/TBD | Not started | - |
| 5. Reliability, Tracing & Eval Baseline | 0/TBD | Not started | - |
