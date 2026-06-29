# Stack Research

**Domain:** Employer due diligence deep-research agent (RU hiring context)
**Researched:** 2026-06-29
**Confidence:** MEDIUM

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12.x | Backend runtime for LangGraph/FastAPI agents | Best compatibility zone across LangGraph/FastAPI ecosystem while keeping modern typing and performance; avoids edge breakage from newest Python majors. |
| LangGraph | 1.2.6 | Multi-step agent orchestration, supervisor/fan-out/merge graph | Production-oriented stateful graph runtime with checkpointing and explicit control flow that fits deep-research pipelines better than linear chains. |
| FastAPI | 0.138.1 | Typed API layer between graph runtime and UI | High-performance ASGI framework with first-class Pydantic v2 support, ideal for strict schemas and predictable contracts. |
| Uvicorn | 0.49.0 | ASGI server for FastAPI in production | Standard FastAPI serving baseline; simple, battle-tested, and supports performance extras via `uvicorn[standard]`. |
| React | 19.2.7 | UI for timeline/verdict review | Current mainstream React line with strong ecosystem compatibility and good fit for data-driven dashboard UX. |
| Vite | 8.1.0 | Frontend build/dev tooling | Current standard for React apps: fast iteration, simple config, strong TypeScript support. |
| TypeScript | 6.0.3 | Type-safe frontend + API contract handling | Stable latest release (not RC), reducing compiler migration risk while enabling strict end-to-end typing. |
| Supabase (Postgres + pgvector + RLS) | Platform current + `supabase` 2.31.0 + `@supabase/supabase-js` 2.108.x | Persistence, vector search, auth-aware access control | Postgres + pgvector keeps transactional data and embeddings together; RLS gives strict tenant/user boundaries for sensitive due-diligence artifacts. |
| Langfuse | Python SDK 4.12.0, JS SDK v5 line (`@langfuse/tracing` 5.5.3, `@langfuse/otel` 5.7.0) | Tracing/observability for each graph node and run | Purpose-built LLM observability with modern OTel-based SDKs and strong agent workflow visibility. |
| DeepEval | 4.0.6 | LLM/agent regression testing in CI | Pytest-native eval framework that integrates with CI and helps catch quality regressions before shipping. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic | 2.9+ | Strict input/output schemas for API and events | Always: validate every boundary (`request`, `graph state`, `timeline event`, `verdict`) to reduce hallucinated structure. |
| langgraph-checkpoint-sqlite | 3.1.0 | Local/dev checkpoint persistence | Use for local and early MVP reliability; switch to durable DB checkpointer for high-concurrency production later. |
| TanStack Query (`@tanstack/react-query`) | 5.101.x | Frontend server-state caching and sync | Use for all timeline/verdict fetches, retries, stale-time tuning, and optimistic UX around report updates. |
| `@opentelemetry/sdk-node` | Current stable (match Langfuse JS docs) | OTel runtime needed by Langfuse JS tracing pipeline | Use when instrumenting Node/SSR/frontend-adjacent services with Langfuse JS SDK. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Python dependency and environment management | Use `uv add`, `uv sync`, `uv run` only; keep lockfile committed for reproducibility. |
| `pytest` | Unit/integration test runner | Base runner for backend tests and DeepEval test suites. |
| `deepeval` CLI | Eval execution in CI | Run `deepeval test run ...` on PRs; start non-blocking, then add quality gates gradually. |
| ESLint + TypeScript strict mode | Frontend quality gates | Enforce no-`any`, strict null checks, and typed API boundaries from day one. |

## Installation

```bash
# Backend (Python, with uv)
uv add langgraph==1.2.6 langchain==1.3.11 fastapi==0.138.1 "uvicorn[standard]==0.49.0" pydantic>=2.9 supabase==2.31.0 langfuse==4.12.0 deepeval==4.0.6 langgraph-checkpoint-sqlite==3.1.0

# Frontend (Node)
npm install react@19.2.7 react-dom@19.2.7 @tanstack/react-query@5.101.1 @supabase/supabase-js@2.108.2
npm install -D vite@8.1.0 typescript@6.0.3

# Langfuse JS tracing (if Node/SSR instrumentation is used)
npm install @langfuse/tracing@5.5.3 @langfuse/otel@5.7.0 @opentelemetry/sdk-node
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI | Django + DRF | Choose only if you need heavy built-in admin/ORM conventions; otherwise FastAPI is a better fit for typed AI APIs. |
| Supabase Postgres + pgvector | Dedicated vector DB (Pinecone/Weaviate) | Choose only if vector scale/search features clearly exceed pgvector needs; early-stage due diligence agent usually benefits from single Postgres source of truth. |
| Langfuse | LangSmith | Choose if team is already standardized on LangChain-native telemetry stack and accepts tighter ecosystem coupling. |
| DeepEval | Ragas/custom eval harness | Choose for narrower RAG-only evaluation or when organization already has mature internal eval platform. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Pydantic v1-era FastAPI patterns | Current FastAPI versions require modern Pydantic v2 semantics; legacy patterns create migration debt and runtime errors. | FastAPI + Pydantic v2 models only. |
| Ad-hoc scraping scripts directly in graph nodes | Blends transport concerns with reasoning logic, hard to test/retry, and causes brittle runs. | Isolate source connectors and keep graph nodes pure/typed. |
| Storing embeddings in a separate system by default | Adds operational complexity and consistency issues before proven need. | Start with Supabase Postgres + pgvector; split later only if metrics demand it. |
| Using Langfuse pre-v4 (Python) or pre-v5 (JS) APIs | Recent SDKs are OTel-centered and older APIs are deprecated patterns. | Use Langfuse Python v4 + JS v5 migration guides and APIs. |
| TypeScript RC compiler for production baseline | RC improves speed but increases toolchain drift risk. | Pin TypeScript stable 6.0.3 for now. |

## Stack Patterns by Variant

**If single-user local copilot MVP:**
- Use LangGraph + FastAPI + SqliteSaver (`langgraph-checkpoint-sqlite`) + local file artifacts.
- Because it minimizes operational overhead while preserving graph architecture needed for production migration.

**If multi-report/team-ready deployment:**
- Use Supabase Postgres + pgvector + strict RLS + background job queue for long-running research.
- Because due-diligence data is sensitive and requires durable storage plus enforceable access boundaries.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `langgraph==1.2.6` | Python `>=3.10` | Use Python 3.12 baseline for safer dependency resolution across agent stack. |
| `fastapi==0.138.1` | `pydantic>=2.9.0` | FastAPI modern line is Pydantic v2-only; do not mix v1 models. |
| `uvicorn==0.49.0` | FastAPI 0.138.x | Use `uvicorn[standard]` in production for better parser/event-loop defaults. |
| `@langfuse/tracing@5.5.3` | Node `>=20` + `@langfuse/otel` 5.x | JS tracing stack depends on OTel pipeline and Node modern runtime. |
| `vite@8.1.0` | Node `20.19+` or `22.12+` | Match Vite runtime requirements in CI and local dev images. |

## Confidence by Recommendation

| Area | Confidence | Reason |
|------|------------|--------|
| Agent/backend stack (LangGraph/FastAPI/Pydantic/Uvicorn) | MEDIUM | Version and compatibility data verified from official docs/package indexes; no Context7 MCP available in this runtime. |
| Data layer (Supabase/Postgres/pgvector/RLS) | MEDIUM | Official Supabase docs strongly align on these patterns; some details vary by deployment model. |
| Observability (Langfuse) | MEDIUM | Official docs and package sources confirm v4/v5 direction; integration shape is clear. |
| Evaluation (DeepEval) | MEDIUM | PyPI + official docs confirm active usage and CI workflow; quality-gate thresholds remain project-specific. |
| Ecosystem trend claims | LOW | Cross-project "standard stack" claims are from broad web synthesis and should not be treated as hard standards. |

## Sources

- [LangGraph install docs](https://docs.langchain.com/oss/python/langgraph/install)
- [LangGraph PyPI](https://pypi.org/project/langgraph/)
- [LangChain install docs](https://docs.langchain.com/oss/python/langchain/install)
- [LangChain PyPI](https://pypi.org/project/langchain/)
- [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/)
- [FastAPI PyPI](https://pypi.org/project/fastapi/)
- [Uvicorn release notes](https://uvicorn.dev/release-notes/)
- [Uvicorn PyPI](https://pypi.org/project/uvicorn/)
- [Supabase AI + pgvector docs](https://supabase.com/docs/guides/ai)
- [Supabase RLS docs](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [supabase-py PyPI](https://pypi.org/project/supabase/)
- [supabase-js npm](https://www.npmjs.com/package/@supabase/supabase-js)
- [Langfuse SDK overview](https://langfuse.com/docs/observability/sdk/overview)
- [Langfuse Python PyPI](https://pypi.org/project/langfuse/)
- [Langfuse tracing npm](https://www.npmjs.com/package/@langfuse/tracing)
- [Langfuse otel npm registry](https://registry.npmjs.org/@langfuse/otel)
- [DeepEval docs](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)
- [DeepEval PyPI](https://pypi.org/project/deepeval/)
- [React npm](https://www.npmjs.com/package/react)
- [Vite guide](https://vite.dev/guide/)
- [Vite npm](https://www.npmjs.com/package/vite)
- [TypeScript npm](https://www.npmjs.com/package/typescript)
- [TanStack Query releases](https://github.com/TanStack/query/releases)

---
*Stack research for: Employer due diligence deep-research agent*
*Researched: 2026-06-29*
