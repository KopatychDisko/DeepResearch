# Architecture Research

**Domain:** Employer due diligence deep-research agent (OSINT-style company investigation)
**Researched:** 2026-06-29
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            Experience Layer                               │
├────────────────────────────────────────────────────────────────────────────┤
│  React UI (query form, timeline, verdict, progress)                      │
│            │                                                              │
│            ▼                                                              │
│  FastAPI HTTP API (submit query, job status, report fetch)               │
├────────────────────────────────────────────────────────────────────────────┤
│                          Orchestration Layer                              │
├────────────────────────────────────────────────────────────────────────────┤
│  Supervisor Graph Node                                                    │
│      ├──▶ News Researcher Subgraph                                        │
│      ├──▶ Reviews Researcher Subgraph                                     │
│      └──▶ HH/Registry Researcher Subgraph                                 │
│                         ▼                                                 │
│                 Merge + Dedup Node                                        │
│                         ▼                                                 │
│                    Verdict Node                                           │
├────────────────────────────────────────────────────────────────────────────┤
│                       Evidence and Infrastructure                          │
├────────────────────────────────────────────────────────────────────────────┤
│ Search/Scrape Tools | Checkpointer | Report Store | Observability         │
│ (Tavily, connectors) | (SqliteSaver) | (JSON timeline) | (Langfuse)      │
└────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| React client | Captures company query, displays progress/events/verdict | React + polling/SSE to FastAPI |
| API gateway | Accepts jobs, validates input, exposes status/report endpoints | FastAPI routes with strict request/response schemas |
| Job controller | Starts graph run and ties run IDs to user job IDs | Service function + checkpointer key mapping |
| Supervisor node | Chooses source agents and task scope for this company | LangGraph node with routing logic |
| Source researcher subgraphs | Collect evidence from one source family and output typed events | LangGraph subgraphs using source-specific connectors |
| Merge + dedup node | Normalizes and deduplicates events across sources | Deterministic merge function with canonical keys |
| Verdict node | Produces risk summary, interview questions, red flags from grounded events | Structured LLM output constrained by evidence IDs |
| Evidence/provenance store | Persists events, source URLs, confidence, run metadata | PostgreSQL/Supabase later, SQLite in early phases |
| Observability | Trace each node/tool call and failure mode | Langfuse traces + structured logs |

## Recommended Project Structure

```
src/
├── api/                     # FastAPI routes and DTO schemas
│   ├── routes/              # submit/status/report endpoints
│   └── schemas/             # request/response models
├── graph/                   # LangGraph orchestration and nodes
│   ├── supervisor/          # routing logic
│   ├── researchers/         # news/reviews/hh subgraphs
│   ├── merge/               # dedup and normalization
│   └── verdict/             # verdict generation
├── connectors/              # external system adapters only (search, hh, etc.)
├── domain/                  # pure models and transformation logic
│   ├── events/              # CompanyEvent and related types
│   └── provenance/          # evidence references and confidence
├── infra/                   # persistence, checkpoints, telemetry wiring
└── ui/                      # React frontend
```

### Structure Rationale

- **`graph/`:** Keeps orchestration explicit and testable as graph contracts.
- **`domain/`:** Isolates pure transformation logic from tool side effects.
- **`connectors/`:** Constrains I/O and external dependencies behind narrow interfaces.
- **`infra/`:** Centralizes checkpointing/telemetry so nodes stay focused on research logic.

## Architectural Patterns

### Pattern 1: Supervisor + Specialist Fan-Out/Fan-In

**What:** A central supervisor routes tasks to specialized source researchers in parallel, then a single merge node performs fan-in.
**When to use:** Multi-source investigations where each source has distinct access patterns and failure modes.
**Trade-offs:** Faster and clearer ownership per source, but needs strict merge contracts and concurrency-safe state keys.

**Example:**
```python
# Supervisor decides which specialists run for this company.
def route_sources(state: ResearchState) -> list[str]:
    targets: list[str] = []
    if state.company_context.news_relevant:
        targets.append("news_researcher")
    if state.company_context.review_relevant:
        targets.append("reviews_researcher")
    if state.company_context.hh_relevant:
        targets.append("hh_researcher")
    return targets
```

### Pattern 2: Evidence-First Pipeline Boundary

**What:** Retrieval output is untrusted input until normalized into typed events with provenance.
**When to use:** Any OSINT/deep-research flow where raw external text can be noisy or adversarial.
**Trade-offs:** Adds extraction/validation steps, but prevents prompt contamination and unsupported claims.

**Example:**
```python
def to_event(record: RawFinding) -> CompanyEvent:
    if record.source_url is None:
        raise ValueError("Missing source_url for event extraction")
    return CompanyEvent(
        date=record.date,
        category=record.category,
        description=record.description,
        source_url=record.source_url,
        confidence=record.confidence,
    )
```

### Pattern 3: Deterministic Merge Before Verdict

**What:** Perform deterministic dedup/sort/canonicalization before any narrative verdict generation.
**When to use:** Multi-source timelines where duplicate stories and date conflicts are common.
**Trade-offs:** More implementation effort than direct summarize-from-raw, but dramatically improves consistency and explainability.

## Data Flow

### Request Flow

```
User submits company name
    ↓
React UI POST /research
    ↓
FastAPI validates and creates job_id
    ↓
Graph run starts with checkpointer thread_id
    ↓
Supervisor routes to source researchers (parallel)
    ↓
Each researcher emits typed evidence events + provenance
    ↓
Merge node deduplicates and sorts timeline
    ↓
Verdict node derives risks/questions/red flags from merged events
    ↓
Persist report JSON + trace metadata
    ↓
UI polls/streams /research/{job_id} and renders timeline + verdict
```

### Trust and Boundary Flow

```
External web/hh/review content (UNTRUSTED)
    ↓ [connector boundary]
Raw findings
    ↓ [normalization boundary]
Typed evidence events with source_url + confidence
    ↓ [merge boundary]
Canonical timeline
    ↓ [verdict boundary]
User-facing summary constrained to evidence IDs
```

### Key Data Flows

1. **Acquisition flow:** Query intent -> source-specific retrieval -> raw findings.
2. **Normalization flow:** Raw findings -> typed event schema -> confidence tagging.
3. **Synthesis flow:** Source event lists -> dedup merge -> timeline ordering -> verdict.
4. **Presentation flow:** Persisted report -> API status/report endpoints -> UI timeline card and verdict card.

## Build Order Implications (for Roadmap)

1. **Domain schema first** (`CompanyEvent`, provenance, confidence enums)  
   Dependency: all nodes and UI depend on stable data contracts.
2. **Single-source vertical slice (News only)**  
   Dependency: validates end-to-end graph + UI loop before multi-source complexity.
3. **Supervisor routing + additional source subgraphs (Reviews, HH)**  
   Dependency: requires stable single-source contracts and connector abstractions.
4. **Deterministic merge/dedup layer**  
   Dependency: needs at least two sources to justify cross-source reconciliation.
5. **Verdict synthesis with strict evidence grounding**  
   Dependency: should consume canonical merged timeline, not raw findings.
6. **Persistence + resume + observability hardening**  
   Dependency: after functional flow exists, then optimize durability/debuggability.

## Anti-Patterns

### Anti-Pattern 1: One giant researcher prompt

**What people do:** Feed all retrieval outputs to one monolithic LLM call.
**Why it's wrong:** Context noise, poor traceability, weak failure isolation.
**Do this instead:** Use specialist subgraphs with explicit intermediate artifacts.

### Anti-Pattern 2: Verdict before deterministic merge

**What people do:** Generate a verdict directly from per-source raw outputs.
**Why it's wrong:** Duplicate events and conflicting dates leak into conclusions.
**Do this instead:** Canonicalize timeline first, then generate verdict from merged events.

### Anti-Pattern 3: Treat retrieved text as instructions

**What people do:** Allow external content to affect control flow or tool behavior.
**Why it's wrong:** Prompt injection and contamination risk in OSINT workflows.
**Do this instead:** Enforce untrusted-input boundary; treat retrieval strictly as evidence data.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Web search provider (Tavily or equivalent) | Connector with retry + structured result schema | Never pass raw snippets directly to verdict node |
| HH/registry/review sources | Source-specific connectors | Keep parsing logic local to each connector |
| LLM provider(s) | Node-level model selection | Smaller model for extraction, stronger model for verdict |
| Langfuse | Trace hooks per node/tool call | Critical for debugging source disagreements |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `api` ↔ `graph` | Typed function calls with run/job IDs | API does not own research logic |
| `graph/researchers` ↔ `graph/merge` | Typed event lists only | Avoid shared mutable ad-hoc state |
| `graph/verdict` ↔ `ui` | Persisted report schema | UI should render contracts, not infer hidden logic |

## Sources

- [LangGraph Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api) (official docs)
- [LangGraph branching/fan-out/fan-in usage](https://docs.langchain.com/oss/python/langgraph/use-graph-api) (official docs)
- [FastAPI background tasks and queue caveat](https://fastapi.tiangolo.com/tutorial/background-tasks/) (official docs)
- [A Multi-Agent Orchestration Framework for Venture Capital Due Diligence](https://arxiv.org/html/2605.13110v1) (research paper)
- [NVIDIA DeepResearch architecture write-up](https://huggingface.co/blog/nvidia/how-nvidia-won-deepresearch-bench) (industry architecture)

---
*Architecture research for: employer due diligence deep-research systems*
*Researched: 2026-06-29*
