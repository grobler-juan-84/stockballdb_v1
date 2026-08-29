"""Deterministic canonical table serialization for fingerprinting."""

from __future__ import annotations

import datetime as dt
import decimal
from decimal import Decimal
from typing import Any

FINGERPRINT_SCHEMA_VERSION = "1.0"
NULL_TOKEN = "\\N"


def format_value(value: Any) -> str:
    if value is None:
        return NULL_TOKEN
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.datetime):
        if value.tzinfo is not None:
            value = value.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, dt.time):
        return value.isoformat(timespec="seconds")
    if isinstance(value, Decimal):
        d = value
        if d.is_nan():
            return "NaN"
        if d.is_infinite():
            return "Infinity" if d > 0 else "-Infinity"
        if d == 0:
            d = abs(d)
        normalized = d.normalize()
        text = format(normalized, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value:
            return "NaN"
        if value == float("inf"):
            return "Infinity"
        if value == float("-inf"):
            return "-Infinity"
        d = Decimal(str(value)).normalize()
        return format_value(d)
    if isinstance(value, decimal.Decimal):
        return format_value(value)
    return str(value)


def serialize_row(columns: list[str], row: dict[str, Any]) -> str:
    parts = [format_value(row.get(c)) for c in columns]
    return "|".join(parts)
