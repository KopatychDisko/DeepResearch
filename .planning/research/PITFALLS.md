# Pitfalls Research

**Domain:** Employer due diligence / company research agent (Russian open-web sources)
**Researched:** 2026-06-29
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: Citation-looking hallucinations

**What goes wrong:**
The agent emits confident claims (dates, layoffs, funding amounts, legal issues) with URLs that do not actually support the claim text, or with generic source pages instead of evidence-level passages.

**Why it happens:**
Generation is allowed before evidence is locked. Teams treat "has a URL" as equivalent to "claim is grounded," and evaluate only final answer fluency, not claim-evidence links.

**How to avoid:**
Implement a strict claim-level cite-or-cut gate: every claim must map to an extracted source quote/span; otherwise downgrade to "unverified" or convert to an interview question. Block verdict generation if unsupported critical claims remain.

**Warning signs:**
- Same source URL reused across many unrelated claims
- High confidence claims with no quoted evidence in intermediate state
- Source page mentions topic broadly but not the reported numbers/dates

**Phase to address:**
Phase 2 (Evidence extraction + provenance enforcement), validated again in Phase 5 (evaluation).

---

### Pitfall 2: Company identity drift (same-name conflation)

**What goes wrong:**
The timeline mixes events from similarly named companies (different legal entities, countries, or industries), producing false red flags.

**Why it happens:**
Name string matching is used as the primary key; ingestion does not require disambiguating identifiers (legal name, registry id, domain, location).

**How to avoid:**
Define a canonical company identity record at the start of each run. Require at least two identity anchors before accepting any event into merge. Quarantine events without clear entity anchors.

**Warning signs:**
- Sources disagree on headquarters/industry but still merge into one company
- Event list contains abrupt context switches (e.g., unrelated products/markets)
- Multiple legal suffix patterns detected for "same" employer

**Phase to address:**
Phase 1 (Query normalization + source retrieval contracts), reinforced in Phase 3 (merge rules).

---

### Pitfall 3: Naive deduplication by text similarity

**What goes wrong:**
Duplicate stories survive as separate events, or distinct events are incorrectly collapsed into one because wording is similar.

**Why it happens:**
Dedup is treated as sentence-level fuzzy matching; event identity dimensions (time window, actors, trigger type, source independence) are ignored.

**How to avoid:**
Use event-level canonicalization first (entity, category, normalized date window, core predicate). Run dedup on structured event signatures, then attach multiple `source_url` values to one canonical event.

**Warning signs:**
- Multiple near-identical layoffs/funding entries within short date windows
- One merged event citing conflicting dates/amounts without contradiction marker
- Dedup precision drops when adding a new source connector

**Phase to address:**
Phase 3 (Cross-source merge + dedup conflict resolution), verified in Phase 5 evals.

---

### Pitfall 4: Treating review/forum sentiment as factual evidence

**What goes wrong:**
Anonymous review claims are promoted to factual timeline events (e.g., "salary delays") without corroboration, distorting verdicts.

**Why it happens:**
Teams optimize for "rich output" and fail to separate weak signals from verified events; credibility weighting is absent.

**How to avoid:**
Model review signals as a separate evidence class with lower default confidence. Require cross-source corroboration before converting sentiment into factual event categories. Keep unverified sentiment in "questions to ask."

**Warning signs:**
- Verdict color flips based on one or two anonymous posts
- No distinction between "reported by reviews" and "verified by independent sources"
- Strong claims without timestamped corroboration

**Phase to address:**
Phase 2 (source-specific extraction policies) and Phase 4 (verdict policy + UX guardrails).

---

### Pitfall 5: Russian-source retrieval degradation hidden as success

**What goes wrong:**
The pipeline silently ingests corrupted or incomplete Russian text (encoding issues, anti-bot fallback pages, JS/obfuscation artifacts) but continues as if retrieval succeeded.

**Why it happens:**
Fetch success is tracked by HTTP status only; no content quality checks exist for encoding validity, text density, or anti-bot markers.

**How to avoid:**
Add retrieval quality gates: charset detection/normalization, anti-bot fingerprint checks, minimum meaningful-text thresholds, and hard fail states when source text is unusable.

**Warning signs:**
- Sudden spike in very short extracted texts from one source family
- High parse success but low fact extraction yield
- Frequent mojibake or repeated placeholder strings in extracted spans

**Phase to address:**
Phase 1 (connector reliability contracts), monitored continuously in Phase 5 (observability/evals).

---

### Pitfall 6: Final-only evaluation (no trajectory checks)

**What goes wrong:**
The team validates only final JSON/verdict shape while intermediate planning, retrieval, and merge errors remain invisible; regressions ship unnoticed.

**Why it happens:**
Evaluation harnesses focus on output schema and snapshot tests, not process-level reliability metrics.

**How to avoid:**
Introduce trajectory-level evals: claim support coverage, unsupported-claim count, contradiction surfacing rate, dedup precision/recall, and identity-drift incidents per run.

**Warning signs:**
- Final schema passes but manual audit finds unsupported critical claims
- Frequent reruns produce materially different high-confidence timelines
- "Looks correct" acceptance without trace replay

**Phase to address:**
Phase 5 (evaluation and observability hardening), with instrumentation hooks designed in Phases 2-3.

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use one LLM pass for extract+merge+verdict | Fast prototype | Untraceable errors; impossible root-cause analysis | Only for throwaway spike |
| Treat URL citation as sufficient grounding | Simple implementation | Hallucinated "sourced" claims | Never |
| Dedup with only embedding similarity | Quick merge logic | False merges/splits in production | MVP only if clearly labeled low-trust |
| Force binary verdict from sparse evidence | Cleaner UI | Overconfident bad decisions | Never |
| Ignore unresolved claims | Fewer warnings | Hidden risk accumulation | Never |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Web search connector | Accept first page snippets as facts | Fetch and verify source page evidence before extraction |
| Russian content sources | Assume UTF-8 and static HTML | Detect charset, support rendered/obfuscated pages, validate extracted text quality |
| Langfuse tracing | Trace only final verdict node | Trace each source researcher + merge decisions + unsupported-claim drops |
| SqliteSaver checkpointer | Persist only final state | Persist intermediate evidence/provenance artifacts for replay/audit |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full-document reprocessing per source | Long run times, rising token cost | Chunking + selective re-read around candidate evidence spans | ~20-50 long pages per run |
| O(n^2) pairwise dedup at merge | Merge latency spikes with more sources | Blocking by category/date/entity before pair comparison | ~100+ raw events |
| No retry budget partition by source | One flaky source stalls whole run | Per-source timeout/retry budget + partial completion semantics | Any unstable source day |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Following prompt-like instructions from fetched pages | Data poisoning / instruction hijack | Treat fetched text as untrusted data only; ignore embedded directives |
| Rendering user/company query directly into crawler requests without normalization | SSRF-like abuse and scope drift | Strict URL/domain allowlists and query normalization before fetch |
| Logging raw extracted sensitive text in traces | Privacy leakage in telemetry | Structured redaction policy for PII and sensitive snippets |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Confidence labels without evidence previews | Users over-trust colored badges | Show claim + evidence snippet + source link together |
| Single red/yellow/green output without uncertainty breakdown | False certainty before interviews | Separate verified risks, weak signals, and open questions |
| Hiding unresolved claims | Users assume completeness | Explicit "Not verified yet" section with next-check suggestions |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Timeline extraction:** Often missing claim-to-quote links — verify each high-confidence event has evidence span.
- [ ] **Deduplication:** Often missing conflict handling — verify conflicting date/amount variants are surfaced, not silently merged.
- [ ] **Verdict:** Often missing uncertainty policy — verify unsupported claims cannot influence color verdict.
- [ ] **Source ingestion:** Often missing content-quality gate — verify anti-bot/encoding failure paths are explicit.
- [ ] **Identity resolution:** Often missing legal-entity anchors — verify same-name disambiguation is mandatory before merge.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Citation-looking hallucinations | MEDIUM | Re-run verification pass, downgrade unsupported claims, regenerate verdict from verified subset only |
| Identity drift conflation | HIGH | Rebuild canonical entity record, purge contaminated merged events, replay merge from raw source evidence |
| Bad dedup merge/split | MEDIUM | Recompute event signatures with stricter keys, run conflict audit report, reissue normalized timeline |
| Russian retrieval corruption | MEDIUM | Re-fetch with charset/render fallback path, quarantine suspect source batch, rerun extraction only for affected sources |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Citation-looking hallucinations | Phase 2 | Unsupported-claim rate near zero for high-confidence claims |
| Company identity drift | Phase 1 | No merged timeline event without entity anchors |
| Naive deduplication | Phase 3 | Dedup precision/recall on golden cross-source set |
| Review-as-fact overreach | Phase 4 | Verdict uses only verified evidence class for hard risk claims |
| Russian retrieval degradation | Phase 1 | Retrieval quality checks catch malformed/unusable content before extraction |
| Final-only evaluation blindness | Phase 5 | Trajectory metrics and trace replay required in CI/UAT |

## Sources

- [Why Your Deep Research Agent Fails?](https://arxiv.org/html/2601.22984v2) (MEDIUM, websearch-verified)
- [A Multi-Agent Orchestration Framework for Venture Capital Due Diligence](https://arxiv.org/html/2605.13110) (MEDIUM, websearch-verified)
- [Harvesting Events from Multiple Sources](https://arxiv.org/html/2406.16021v1) (MEDIUM, websearch-verified)
- [Joint Document-Level Event Extraction via TTPCG](https://aclanthology.org/2023.acl-long.584.pdf) (MEDIUM, websearch-verified)
- [When it's all piling up: error propagation in NLP pipeline](https://ceur-ws.org/Vol-1386/piling_up.pdf) (MEDIUM, websearch-verified)
- [How to Interpret Glassdoor Reviews with Skepticism](https://www.resumly.ai/blog/how-to-interpret-glassdoor-reviews-with-skepticism) (LOW, supporting only)
- [How to interpret anonymous company reviews](https://www.themuse.com/advice/heres-how-to-interpret-anonymous-company-reviews-correctly) (LOW, supporting only)

---
*Pitfalls research for: Employer due diligence agent*
*Researched: 2026-06-29*
