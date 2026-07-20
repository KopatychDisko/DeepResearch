"""HTML helpers shared by hh.ru API and website parsers."""

from __future__ import annotations

import re


def strip_html(raw_html: str) -> str:
    """Remove HTML tags from hh.ru vacancy descriptions for LLM consumption."""
    text: str = re.sub(r"<[^>]+>", "\n", raw_html)
    return re.sub(r"\n{2,}", "\n", text).strip()
