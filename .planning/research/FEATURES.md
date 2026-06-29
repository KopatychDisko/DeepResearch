# Feature Research

**Domain:** Employer due diligence agent for job seekers (Russian-language open sources)
**Researched:** 2026-06-29
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-source employer profile (news + employee reviews + job board footprint) | Job seekers expect one place to evaluate employer reputation quickly | MEDIUM | Must unify heterogeneous sources and preserve source URLs per claim |
| Structured timeline of major employer events | Candidates want chronology (layoffs, leadership changes, scandals, funding) before interviews | HIGH | Requires event extraction, date normalization, and conflict handling across sources |
| Compensation and benefits signal extraction | Salary/fairness context is a standard decision factor in employer research | MEDIUM | Use confidence-tagged ranges and source attribution; avoid false precision |
| Interview process intelligence | Platforms like Glassdoor normalize sharing interview questions and process patterns | MEDIUM | Aggregate recurring themes, not one-off anecdotes |
| Risk/red-flag summary with evidence links | Users expect concise "should I worry?" output, not raw documents | MEDIUM | Must always link red flags to supporting sources and timestamps |
| Confidence scoring and citation transparency | Trust is now baseline; unsupported claims reduce usefulness | MEDIUM | Per-fact confidence plus URL citation is mandatory for due diligence outputs |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Adaptive source orchestration per company | Avoids fixed pipelines and improves relevance/cost by selecting only useful sources | HIGH | Supervisor chooses source agents dynamically based on company signal availability |
| Cross-source semantic deduplication with merged evidence | Produces cleaner timeline than naive aggregation and increases user trust | HIGH | Merge equivalent events into one canonical event with multiple source URLs |
| Verdict blocks tailored for interview prep (risks, questions, red flags) | Converts research into direct user action for upcoming interviews | MEDIUM | Aligns output to user decision workflow, not generic company analytics |
| Narrative drift detection across source types | Highlights mismatch between official messaging and employee/community signals | HIGH | Compare "owned" narrative with third-party sentiment over time |
| Explainable uncertainty diagnostics | Makes low-confidence findings actionable instead of silently dropped | MEDIUM | Show why confidence is low (source conflict, stale signal, sparse evidence) |
| Longitudinal employer change tracking for repeat checks | Supports repeated pre-interview use for the same employer over time | HIGH | Needs snapshot persistence and delta computation between runs |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Opaque single "employer score" ranking | Users want fast comparison | Hides uncertainty, amplifies source bias, and creates explainability/trust risk | Keep multi-dimensional verdict with evidence-backed sub-scores |
| Fully autonomous pass/fail hiring advice | Feels convenient ("just tell me yes/no") | Overclaims model certainty and increases legal/ethical risk in employment context | Provide decision support: risks + interview questions + evidence |
| Real-time continuous monitoring in v1 | Sounds advanced and proactive | High infra + scraping maintenance burden; weak fit for on-demand interview prep | On-demand reports with optional scheduled refresh later |
| Social scraping without provenance controls | Promises broader coverage | High noise/manipulation risk; weak defensibility without source quality controls | Whitelist sources, store provenance, and enforce confidence thresholds |
| Unbounded source expansion (global + all languages) | Appears to increase coverage | Dilutes relevance for Russian-market interviews and hurts data quality early | Keep RU-focused source set in v1, expand only after validated quality |

## Feature Dependencies

```
Source connectors
    └──requires──> Canonical schema + source provenance
                         └──requires──> Event extraction + normalization
                                              └──requires──> Entity resolution + semantic dedup
                                                                   └──requires──> Timeline + verdict generation

Confidence scoring ──requires──> Citation capture + evidence conflict detection

Interview-prep verdict blocks ──enhances──> Timeline of events

Opaque single-score ranking ──conflicts──> Explainable confidence + evidence transparency
```

### Dependency Notes

- **Timeline + verdict requires dedup first:** Without canonicalized events, user output repeats the same story and looks unreliable.
- **Confidence requires provenance capture:** Confidence labels are not credible unless each claim is tied to source URLs and extraction context.
- **Interview guidance depends on risk classification:** Questions-to-ask are generated from verified risk patterns, not generic templates.
- **Single-score ranking conflicts with transparency goals:** Compressing to one score removes the evidence shape users need for due diligence.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] Multi-source employer ingestion (news, reviews, hh/job-board signal) — validates core data coverage
- [ ] Structured event timeline with dedup + citations + confidence — validates trustworthiness of core output
- [ ] Actionable verdict blocks (risks, interview questions, red flags) — validates practical pre-interview utility

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Longitudinal re-check comparisons for the same company — add when repeat usage pattern is confirmed
- [ ] Narrative drift analytics by source cluster — add when users need deeper interpretation than v1 verdict

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Broader multilingual/non-RU source expansion — defer until RU pipeline quality is consistently high
- [ ] Optional continuous monitoring mode — defer until on-demand workflow is stable and cost-understood

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Multi-source ingestion + canonical schema | HIGH | MEDIUM | P1 |
| Timeline extraction + semantic dedup + citations | HIGH | HIGH | P1 |
| Verdict blocks for interview prep | HIGH | MEDIUM | P1 |
| Longitudinal delta tracking | MEDIUM | HIGH | P2 |
| Narrative drift analytics | MEDIUM | HIGH | P2 |
| Continuous monitoring mode | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Competitor A | Competitor B | Our Approach |
|---------|--------------|--------------|--------------|
| Company reviews + ratings + interview signals | Glassdoor has mature crowd signals and interview experience content | Indeed has broader listings but weaker deep employer due diligence focus | Fuse review-like signals with timeline-first synthesis and evidence traceability |
| AI-era employer narrative visibility | Built In Employer Intelligence emphasizes AI/search perception analytics for employers | PerceptionX/BrandScore focus on employer brand visibility in LLM answers | Adapt concept for job seekers: detect signal mismatches and surface decision-relevant risks |
| Actionability for candidate decisions | Most products emphasize data display over interview decision support | Employer-side tools focus on brand control, not candidate risk navigation | Prioritize interview-ready verdict output tied directly to source-backed findings |

## Sources

- https://jobright.ai/blog/indeed-vs-glassdoor/
- https://bestjobsearchapps.com/articles/en/glassdoor-company-research-evaluation-reviews-ratings-salary-data-guide-for-2026-job-searches
- https://builtin.com/articles/built-ins-ai-employer-intelligence-platform
- https://www.prnewswire.com/news-releases/built-in-launches-the-first-employer-intelligence-platform-for-the-ai-driven-hiring-era-302761984.html
- https://www.perceptionx.ai/visibility-index
- https://consilium.law/sparkpoint/ai-hiring-discrimination/
- https://natlawreview.com/article/auditing-artificial-intelligence-systems-bias-employment-decision-making
- https://data.aclum.org/wp-content/uploads/2025/01/EOCC_www_eeoc_gov_laws_guidance_select-issues-assessing-adverse-impact-software-algorithms-and-artificial.pdf
- https://www.promptcloud.com/blog/job-posting-data-aggregation/
- https://jobspipe.dev/guides/how-to-build-a-job-aggregator

---
*Feature research for: employer due diligence agent*
*Researched: 2026-06-29*
