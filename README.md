# Employer Due Diligence Agent

AI-powered employer research for job seekers. Enter a company name — get a structured verdict with red flags, risks, and source links in minutes.

Built with **LangGraph**, **FastAPI**, and **React**. Supports **Russian** and **English** UI and responses.

---

## What it does

1. **Resolves company identity** — web search + LLM; if several matches exist, you pick the right one
2. **Researches in parallel** — news, employee reviews, hh.ru hiring signals
3. **Builds a timeline** — merges and deduplicates events from all sources
4. **Generates a verdict** — score 1–10, summary, red flags, risks, interesting facts

Every claim is tied to a source URL.

---

## Quick start

### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ (frontend build)
- API keys: [OpenRouter](https://openrouter.ai/) or OpenAI/Google, plus [Tavily](https://tavily.com/)

### Setup

```bash
git clone <your-repo-url>
cd deep_resaerch

cp .env.example .env
# Fill in OPENROUTER_API_KEY (or OPENAI_API_KEY) and TAVILY_API_KEY

./start.sh
```

Opens at **http://127.0.0.1:8000** — builds the frontend and starts the server.

### CLI (one-shot run)

```bash
uv run python scripts/e2e_run.py "Яндекс"
```

---

## Configuration

Copy `.env.example` → `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | one of LLM keys | Default LLM provider |
| `OPENAI_API_KEY` | one of LLM keys | Alternative provider |
| `GOOGLE_API_KEY` | one of LLM keys | Alternative provider |
| `TAVILY_API_KEY` | yes | Web search |
| `LLM_MODEL` | no | Default: `openai:gpt-5-mini` |
| `LANGFUSE_PUBLIC_KEY` | no | Observability (Langfuse) |
| `LANGFUSE_SECRET_KEY` | no | Observability (Langfuse) |
| `LANGFUSE_BASE_URL` | no | e.g. `https://us.cloud.langfuse.com` |

---

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│  React UI   │────▶│  FastAPI                                     │
│  RU / EN    │     │  POST /runs  ·  GET /runs/{id}  ·  /identity │
└─────────────┘     └────────────────────┬─────────────────────────┘
                                         │
                         ┌───────────────▼───────────────┐
                         │  LangGraph pipeline           │
                         │                               │
                         │  resolve_identity             │
                         │       ↓                       │
                         │  supervisor (tool loop)       │
                         │    · search_news              │
                         │    · search_reviews           │
                         │    · search_hh                │
                         │       ↓                       │
                         │  structure_events → merge     │
                         │       ↓                       │
                         │  generate_verdict             │
                         └───────────────┬───────────────┘
                                         │
                         ┌───────────────▼───────────────┐
                         │  Tavily  ·  OpenRouter LLM    │
                         │  Langfuse (optional traces)   │
                         └───────────────────────────────┘
```

**Human-in-the-loop:** if identity is ambiguous, the run pauses at `awaiting_input`. Pick a company in the UI — research continues automatically.

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/runs?background=true` | Start async research |
| `GET` | `/runs/{run_id}` | Poll status and result |
| `POST` | `/runs/{run_id}/identity` | Confirm company after ambiguous match |
| `POST` | `/runs/{run_id}/resume` | Resume interrupted run |

Example:

```bash
curl -X POST http://127.0.0.1:8000/runs?background=true \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Яндекс", "response_language": "ru"}'
```

---

## Development

```bash
# Install dependencies
uv sync

# Run tests (excludes eval suite)
uv run pytest

# Frontend dev server (proxies to API)
cd frontend && npm install && npm run dev

# API only
uv run uvicorn employer_dd_agent.main:app --reload
```

---

## Tech stack

| Layer | Tools |
|-------|-------|
| Orchestration | LangGraph, LangChain |
| API | FastAPI, Uvicorn |
| LLM | OpenRouter / OpenAI / Google via LangChain |
| Search | Tavily |
| Frontend | React 19, TypeScript, Vite |
| Observability | Langfuse (optional) |
| Quality | pytest, DeepEval (eval suite) |

---

## Project structure

```
src/employer_dd_agent/   # Backend: graph, API, sources, verdict
frontend/                # React UI
tests/                   # Unit tests
scripts/e2e_run.py       # CLI smoke test
eval/                    # DeepEval datasets (optional)
```

---

## License

Private / unlicensed — add a license before public distribution if needed.
