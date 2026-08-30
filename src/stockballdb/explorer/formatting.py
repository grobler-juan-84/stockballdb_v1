"""Display formatting for Explorer (presentation only)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any


NULL_DISPLAY = "—"


def format_cell(value: Any) -> str:
    if value is None:
        return NULL_DISPLAY
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, dt.time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f").rstrip("0").rstrip(".") or "0"
    return str(value)


def format_hash(value: str | None, *, prefix_len: int = 16) -> str:
    if not value:
        return NULL_DISPLAY
    if len(value) <= prefix_len + 10:
        return value
    return f"{value[:prefix_len]}…"


def rows_to_display_dicts(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{k: format_cell(v) for k, v in row.items()} for row in rows]
