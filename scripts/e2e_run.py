#!/usr/bin/env python3
"""Run a one-shot end-to-end due diligence check from the CLI."""

from __future__ import annotations

import json
import sys

from dotenv import load_dotenv

from agents.observability import initialize_observability
from agents.models import RunRequest
from backend.run_service import run_research_pipeline


def main(argv: list[str]) -> int:
    load_dotenv()
    initialize_observability()
    if len(argv) < 2:
        print("Usage: uv run python scripts/e2e_run.py <company_name>", file=sys.stderr)
        return 2

    company_name: str = argv[1].strip()
    if len(company_name) < 2:
        print("company_name must be at least 2 characters", file=sys.stderr)
        return 2

    request = RunRequest(company_name=company_name)
    print("Running synchronous pipeline...", flush=True)
    run_id, result = run_research_pipeline(request=request, run_id=None)
    payload: dict[str, object] = {
        "run_id": str(run_id),
        "company": result.identity.canonical_name,
        "verdict_color": result.verdict.color.value,
        "timeline_events": len(result.timeline.events),
        "findings": len(result.findings),
        "verdict_summary": result.verdict.summary,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
