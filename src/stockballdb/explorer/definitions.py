"""Load field definitions from authoritative docs for Explorer tooltips."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from stockballdb.health.provenance import repo_root

_DEFINITIONS_PATH = repo_root() / "docs" / "StockBallDB_definitions.md"

# Fallback snippets for key confusing fields when doc parse misses.
_FALLBACK: dict[str, str] = {
    "return_1d": "One-session return derived from adjusted close (decimal, not percent).",
    "drawdown_from_high": "Drawdown from rolling high based on adjusted close.",
    "return_5d": "Forward return over 5 trading sessions (ex-post label).",
    "return_20d": "Forward return over 20 trading sessions (ex-post label).",
    "fed_funds_rate": "Effective federal funds rate; stored as decimal percent points per definitions.",
    "inflation_rate": "Headline CPI inflation; macro percentage-point convention per Phase 4A.",
    "release_session": "When the event occurs relative to the equity session.",
    "days_since_last_fomc": "Trading sessions since last FOMC event day on spine.",
    "holiday_type": "NYSE holiday classification from calendar derivation.",
}


@lru_cache(maxsize=1)
def _load_definitions_text() -> str:
    if not _DEFINITIONS_PATH.exists():
        return ""
    return _DEFINITIONS_PATH.read_text(encoding="utf-8")


def _parse_field_blocks(text: str) -> dict[str, str]:
    """Extract `field_name` → description from markdown bullet patterns."""
    out: dict[str, str] = {}
    current_table = ""
    for line in text.splitlines():
        if line.startswith("## "):
            current_table = line[3:].strip().lower().replace("`", "")
        m = re.match(r"^\s*[-*]\s+`([a-zA-Z0-9_]+)`\s*[—–-]\s*(.+)$", line)
        if m:
            field, desc = m.group(1), m.group(2).strip()
            out[field] = desc
        m2 = re.match(r"^\s*[-*]\s+\*\*`([a-zA-Z0-9_]+)`\*\*\s*[—–-]\s*(.+)$", line)
        if m2:
            field, desc = m2.group(1), m2.group(2).strip()
            out[field] = desc
    return out


@lru_cache(maxsize=1)
def field_definitions() -> dict[str, str]:
    parsed = _parse_field_blocks(_load_definitions_text())
    merged = dict(_FALLBACK)
    merged.update(parsed)
    return merged


def definition_for(field: str) -> str | None:
    return field_definitions().get(field)


def clear_definitions_cache() -> None:
    _load_definitions_text.cache_clear()
    field_definitions.cache_clear()
