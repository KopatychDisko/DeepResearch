# Project Research Summary

**Project:** Employer Due Diligence Agent
**Domain:** Employer due diligence deep-research system for Russian-language open sources
**Researched:** 2026-06-29
**Confidence:** MEDIUM

## Executive Summary

This project is a decision-support deep-research product for job seekers: it ingests heterogeneous employer signals (news, reviews, job-board footprint), converts them into a canonical timeline, and outputs interview-ready verdict blocks (risks, red flags, and questions to ask). Expert implementations in this domain converge on a supervisor-led multi-agent pipeline, strict typed contracts, and evidence-first processing where external text is treated as untrusted input until normalized into provenance-backed events.

The recommended approach is a phased architecture: start with strict domain schemas and a single-source vertical slice, then add source fan-out, deterministic cross-source merge/dedup, and only then verdict synthesis. Stack choices should stay conservative and production-oriented: Python 3.12 + LangGraph + FastAPI + Pydantic v2 for orchestration/API contracts, React + TypeScript for review UX, Supabase Postgres/pgvector for durable evidence storage, and Langfuse/DeepEval for traceability and regression control.

The main risks are not basic coding errors but trust failures: citation-looking hallucinations, same-name company conflation, brittle dedup logic, and silent retrieval degradation on Russian sources. Mitigation requires hard gates (cite-or-cut, identity anchors, retrieval quality checks), deterministic merge before narrative generation, and trajectory-level evaluation that verifies intermediate evidence quality, not only final JSON shape.

## Key Findings

### Recommended Stack

Research strongly supports a typed, graph-native backend with explicit observability. The stack is well aligned with the target workflow (long-running, multi-step, evidence-driven jobs) and avoids premature platform complexity while preserving a clean upgrade path from local MVP to team-ready deployment.

**Core technologies:**
- `Python 3.12.x` + `LangGraph 1.2.6` + `FastAPI 0.138.1` + `Pydantic v2` + `Uvicorn 0.49.0` for typed orchestration and API boundaries.
- `React 19` + `TypeScript 6` + `Vite 8` for timeline/verdict UI with strict API contract rendering.
- `Supabase (Postgres + pgvector + RLS)` for durable evidence/provenance persistence with strong access boundaries.
- `Langfuse` for node-level traces and `DeepEval` for CI-style quality regression checks.

Critical version constraints include FastAPI with Pydantic v2 semantics, Node runtime compatibility for Vite/Langfuse JS instrumentation, and pinned stable compiler/tooling versions to avoid drift during early phases.

### Expected Features

Launch quality depends on completing a compact set of table-stakes features and resisting seductive anti-features that weaken trust. Product value comes from evidence-backed synthesis, not from surface-level scoring gimmicks.

**Must have (table stakes):**
- Multi-source employer profile ingestion with source URLs preserved per claim.
- Structured timeline extraction with cross-source dedup, confidence tags, and citations.
- Actionable verdict blocks for interview prep: risks, red flags, and targeted questions.

**Should have (competitive):**
- Adaptive source orchestration per employer context (avoid fixed all-source pipelines).
- Cross-source semantic dedup that merges equivalent events into canonical records.
- Explainable uncertainty diagnostics (why confidence is low, not just low labels).

**Defer (v2+):**
- Continuous real-time monitoring mode.
- Broad multilingual/global source expansion beyond RU focus.
- Any opaque single-score ranking that hides evidence structure.

### Architecture Approach

The recommended architecture is Supervisor -> specialist source subgraphs -> deterministic merge/dedup -> verdict synthesis, exposed through a typed FastAPI layer and rendered by a React client. The core pattern is an evidence-first boundary: external retrieval remains untrusted until normalized into typed event records with provenance, and user-facing narrative is constrained to those canonical evidence IDs.

**Major components:**
1. API/job control layer (`FastAPI`) for validated submit/status/report contracts.
2. Graph orchestration layer (`LangGraph`) with supervisor routing and source-specialist subgraphs.
3. Domain + merge layer for canonical event schema, identity resolution, and deterministic dedup.
4. Verdict layer that derives interview guidance from merged evidence only.
5. Infra layer for checkpointing, persistence, and observability.

### Critical Pitfalls

Top risks and prevention strategies that must be enforced by design:

1. **Citation-looking hallucinations** — enforce claim-level cite-or-cut gates; unsupported critical claims must not enter verdict.
2. **Company identity drift** — require canonical identity with multiple anchors before merge; quarantine ambiguous events.
3. **Naive text-similarity dedup** — dedup on structured event signatures (entity, category, date window, predicate), not raw text.
4. **Review sentiment treated as fact** — keep review/forum signals as lower-confidence class unless independently corroborated.
5. **Silent RU retrieval degradation** — add quality gates for encoding, anti-bot markers, and minimum meaningful-text thresholds.

## Implications for Roadmap

Based on combined research, suggested phase structure:

### Phase 1: Identity + Retrieval Foundation
**Rationale:** All downstream trust depends on clean entity resolution and reliable source ingestion.
**Delivers:** Query normalization, canonical company identity record, RU connector contracts, retrieval quality gates, and typed raw-finding schema.
**Addresses:** Multi-source ingestion prerequisite from FEATURES.
**Avoids:** Identity drift conflation and silent RU retrieval corruption.

### Phase 2: Evidence Normalization + Provenance Enforcement
**Rationale:** Verdict quality is bounded by evidence quality; unsupported claims must be impossible by design.
**Delivers:** Source-specific extraction policies, typed event schema (`date/category/description/source_url/confidence`), quote/span provenance capture, claim support validation.
**Uses:** LangGraph + Pydantic v2 + strict API/domain models.
**Implements:** Evidence-first trust boundary pattern.
**Avoids:** Citation-looking hallucinations and review-as-fact overreach.

### Phase 3: Cross-Source Merge and Dedup Engine
**Rationale:** Canonical timeline quality is the central product trust lever and must precede narrative synthesis.
**Delivers:** Deterministic canonicalization, conflict surfacing (date/amount contradictions), semantic dedup over event signatures, ordered timeline artifact.
**Addresses:** Timeline + dedup + citation P1 feature core.
**Implements:** Fan-in merge boundary from architecture research.
**Avoids:** Naive dedup false merges/splits.

### Phase 4: Verdict and Interview-Prep UX
**Rationale:** User value arrives when evidence is translated into actionable interview decisions.
**Delivers:** Risk/red-flag/question blocks, uncertainty diagnostics, timeline/verdict UI cards, explicit verified-vs-weak-signal separation.
**Addresses:** Actionable verdict P1 and explainability differentiator.
**Implements:** Verdict node constrained to canonical evidence IDs.
**Avoids:** Opaque single-score anti-feature and false certainty UX.

### Phase 5: Evaluation, Observability, and Reliability Hardening
**Rationale:** Process-level regressions are otherwise invisible; final-shape checks alone are insufficient.
**Delivers:** Trajectory-level eval suite (claim support rate, dedup precision/recall, identity-drift incidents), Langfuse node-level tracing, replayable checkpoints, CI integration.
**Uses:** DeepEval + Langfuse + checkpoint persistence.
**Addresses:** Quality stabilization before broader rollout.
**Avoids:** Final-only evaluation blindness and hard-to-debug production drift.

### Phase Ordering Rationale

- The order follows hard dependencies: identity/retrieval -> evidence normalization -> merge -> verdict -> quality hardening.
- It groups components by architectural boundaries (connectors/domain/merge/verdict/infra) to reduce cross-phase coupling.
- It mitigates highest-impact pitfalls early, especially trust and provenance failures that can invalidate later UX polish.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** RU-source connector reliability and anti-bot/encoding handling specifics vary significantly by source family.
- **Phase 3:** Dedup conflict policy and metric thresholds (precision/recall trade-offs) need dataset-specific calibration.
- **Phase 5:** Evaluation harness design (golden sets, trajectory metrics, CI gates) requires careful project-specific methodology.

Phases with standard patterns (can usually skip extra research-phase):
- **Phase 2:** Typed schema design + provenance enforcement are well-established in evidence-centric pipelines.
- **Phase 4:** FastAPI/React delivery of timeline and verdict contracts follows common full-stack implementation patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Official docs and package metadata are strong, but final pinning still needs runtime integration validation. |
| Features | MEDIUM | Market expectations and differentiation are clear, but some competitor signals are secondary web sources. |
| Architecture | MEDIUM | Pattern fit is strong and source-supported; real-world complexity depends on source volatility and data quality. |
| Pitfalls | MEDIUM | Risks are consistent with research literature and domain experience; project-specific incidence rates remain to be measured. |

**Overall confidence:** MEDIUM

### Gaps to Address

- **Golden evaluation dataset design:** Define representative employer set and scoring rubric before hard CI quality gates.
- **Source reliability matrix for RU ecosystem:** Benchmark connector success/quality by source type to inform retry/time-budget policy.
- **Entity disambiguation policy depth:** Confirm minimum anchor set (legal name/domain/location/registry) against real ambiguous cases.
- **Confidence calibration:** Convert heuristic confidence labels into measurable thresholds tied to corroboration and evidence quality.

## Sources

### Primary (HIGH confidence)
- Official docs/package pages cited in `STACK.md` (`LangGraph`, `FastAPI`, `Uvicorn`, `Supabase`, `Langfuse`, `DeepEval`, `Vite`, `TypeScript`, `React`, `TanStack Query`).

### Secondary (MEDIUM confidence)
- Architecture and multi-agent research/industry references cited in `ARCHITECTURE.md` and `PITFALLS.md` (LangGraph architecture docs, due-diligence orchestration papers, event extraction and pipeline reliability literature).

### Tertiary (LOW confidence)
- Competitive/market interpretation sources from `FEATURES.md` (blog/news-style analyses and vendor pages), useful for direction but requiring validation during implementation.

---
*Research completed: 2026-06-29*
*Ready for roadmap: yes*
