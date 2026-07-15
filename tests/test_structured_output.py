from __future__ import annotations

import pytest

from employer_dd_agent.models import StructuredCompanyEvents
from employer_dd_agent.structured_output import coerce_structured_output


def test_coerce_structured_output_repairs_broken_json_string() -> None:
    broken_json: str = (
        "{'events': [{'date': '2024-01-01', 'category': 'product', "
        "'description': 'Launch', 'source_url': 'https://example.com', "
        "'confidence': 'high',}]}"
    )
    parsed = coerce_structured_output(
        output=broken_json,
        model_class=StructuredCompanyEvents,
    )
    assert len(parsed.events) == 1
    assert parsed.events[0].description == "Launch"


def test_coerce_structured_output_repairs_markdown_wrapped_json() -> None:
    wrapped_json: str = """```json
{
  "events": [
    {
      "date": null,
      "category": "review_signal",
      "description": "Delayed salaries mentioned",
      "source_url": "https://example.com/review",
      "confidence": "medium"
    }
  ]
}
```"""
    parsed = coerce_structured_output(
        output=wrapped_json,
        model_class=StructuredCompanyEvents,
    )
    assert len(parsed.events) == 1
    assert parsed.events[0].category.value == "review_signal"
