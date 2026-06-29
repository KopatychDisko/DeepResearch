# Employer Due Diligence Agent

## What This Is

A personal LangGraph-based research agent that, given an employer company name, gathers information from open Russian-language sources (news, reviews, social/Telegram mentions, hh.ru) and produces a structured JSON timeline of company events plus a verdict summary for use before applying or interviewing. Built as a portfolio-quality deep-research system on a custom domain model — not a fork of existing reference implementations.

## Core Value

Before every interview, you can run one query on a company name and get a trustworthy, source-backed timeline and verdict — so you walk in knowing what matters, not guessing.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can submit a company name and receive a structured JSON timeline of events (funding, leadership, layoffs, scandal, product, review_signal)
- [ ] Each event includes date (nullable), category, description, source_url, and confidence level
- [ ] LangGraph pipeline runs Supervisor → parallel source researchers (News, Reviews, HH) → Merge → Verdict
- [ ] Supervisor selects relevant sources per company (not all companies have HH profiles or public channels)
- [ ] Merge agent deduplicates semantically similar events across sources, sorts by date, collapses duplicates with multiple source_urls
- [ ] Verdict agent produces green/yellow/red summary with separate blocks: risks, questions to ask in interview, red flags
- [ ] SqliteSaver checkpointer enables long-running research with intermediate progress visibility
- [ ] React UI displays timeline visualization and verdict card
- [ ] Langfuse traces each source agent separately for observability
- [ ] End-to-end flow works: company name → timeline JSON → verdict in UI

### Out of Scope

- Closed sources requiring login (LinkedIn, etc.) — only open web search in v1
- Real-time company monitoring — on-demand queries only
- Foreign/non-Russian companies in v1 — focus on Russian-language sources (hh, Habr Career, otzovik, news aggregators)
- Public SaaS / multi-user product in v1 — personal copilot only
- Mandatory eval quality gate thresholds blocking v1 ship — evals are built but not gating release
- Forking event-deep-research — reference only for patterns, own repo and data schema

## Context

**Problem:** Before interviews, manually researching an employer across news, reviews, hh.ru, and Telegram is slow and inconsistent. Top "deep research" agents solve similar problems but not this specific domain.

**Personal use:** Run before every real job interview to know funding rounds, leadership changes, layoffs, scandals, and review signals.

**Portfolio use:** Demonstrates the same class of work as event-deep-research / open_deep_research agents, with a custom domain model and own implementation.

**Architectural reference (read-only, not forked):** [event-deep-research](https://github.com/bernatsampera/event-deep-research) — study locally via `git clone` into a separate read-only folder. Patterns to borrow:
- LangGraph Supervisor with Research/Think/Finish tools
- Text chunking before event extraction (`chunk_llm_model`)
- Retry logic on structured output (`max_structured_output_retries`)
- Model separation per node (`llm_model`, `structured_llm_model`, `tools_llm_model`)
- Merge graph for cross-source event deduplication

**Graph architecture:**

```
START
  │
  ▼
Supervisor (tools: search_news, search_reviews, search_hh, finish)
  │
  ├──fan-out──▶ News Researcher ──┐
  ├──fan-out──▶ Reviews Researcher├──▶ Merge Agent ──▶ Verdict Agent ──▶ END
  └──fan-out──▶ HH Researcher ────┘
```

**Structured event schema:**

```python
class CompanyEvent(BaseModel):
    date: str | None
    category: Literal["funding", "leadership", "layoffs", "scandal", "product", "review_signal"]
    description: str
    source_url: str
    confidence: Literal["high", "medium", "low"]
```

**Eval hypotheses (built in later phases, not blocking v1):**
1. Recall — golden dataset of N companies with known events
2. Date/fact accuracy — no hallucinated dates; assert source_url matches source text
3. Deduplication — same story from two sources collapses to one event
4. Speed/cost — tokens and time per report; justify small model for chunking vs large for verdict

**Existing workspace:** Brownfield directory with GSD tooling installed; application code not yet built. Codebase map skipped at user request.

## Constraints

- **Tech stack**: Python, LangGraph, FastAPI (backend); React (frontend); Tavily or existing web search tools; Supabase/Postgres for report caching (later phase); Langfuse (observability); DeepEval (evaluation)
- **Scope**: Russian-language sources only in v1
- **Architecture**: Own repository, own commit history, own data schema — no fork of reference project
- **Implementation**: Functional style preferred; LangGraph nodes as pure functions where possible; OOP only for external system connectors
- **Quality**: Hallucinations in dates and monetary amounts are unacceptable even in v1 design — structured output must be source-grounded

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Personal copilot only in v1 | Fastest path to daily utility; no multi-tenant complexity | — Pending |
| Verdict with structured blocks (risks, interview questions, red flags) | More actionable than color-only verdict before interviews | — Pending |
| v1 done = end-to-end UI flow, evals not gating | Ship working product first; quality metrics inform iteration | — Pending |
| Reference event-deep-research read-only | Borrow patterns without inheriting schema or history | — Pending |
| Vertical MVP slices (News first, then fan-out, then UI, then evals, then Supabase cache) | De-risks graph complexity; each phase delivers working increment | — Pending |
| Russian sources only | User's actual interview context; reduces search noise | — Pending |
| Skip codebase mapping | User chose to proceed without /gsd-map-codebase | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-29 after initialization*
