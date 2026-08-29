"""Utilities for exact rebuild against a clean database target."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

CANONICAL_TABLES_TRUNCATE_ORDER = (
    "calendar_context",
    "macro_conditions",
    "market_outcomes",
    "asset_regimes",
    "daily_market_data",
    "scheduled_events",
    "trading_days",
)


def truncate_canonical_tables(engine: Engine) -> None:
    """Remove all canonical rows before an exact rebuild."""
    tables = ", ".join(CANONICAL_TABLES_TRUNCATE_ORDER)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
