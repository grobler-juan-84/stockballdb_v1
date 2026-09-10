"""Display formatting for Explorer (presentation only)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

NULL_DISPLAY = "—"

# Macro rate/spread fields: FRED-native percentage *points* (3.0 = 3%).
# Authority: docs/StockBallDB_definitions.md §Percentage Representation + Phase 4A.
# Do NOT ×100 for on-screen display.
MACRO_PERCENTAGE_POINT_COLUMNS: frozenset[str] = frozenset(
    {
        "inflation_rate",
        "core_inflation_rate",
        "unemployment_rate",
        "fed_funds_rate",
        "treasury_2y_yield",
        "treasury_10y_yield",
        "yield_curve_10y_2y",
        "credit_spread",
    }
)

# Explicit decimal-ratio columns (0.05 = +5%) from definitions / models.
# Authority: StockBallDB_definitions.md — “Unless otherwise specified, percentage
# fields are stored as decimal returns.”
_EXPLICIT_DECIMAL_RATIO_COLUMNS: frozenset[str] = frozenset(
    {
        # daily_market_data
        "return_1d",
        "gap_pct",
        "intraday_return",
        "range_pct",
        "drawdown_from_high",
        # market_outcomes / asset_regimes returns
        "return_3d",
        "return_5d",
        "return_10d",
        "return_20d",
        "return_60d",
        # asset_regimes distances / drawdown / vol (same decimal convention)
        "distance_20dma_pct",
        "distance_50dma_pct",
        "distance_200dma_pct",
        "drawdown_pct",
        "volatility_20d",
    }
)

# Already 0–100 style percentages (health coverage) — never ×100 again.
_ALREADY_PERCENT_POINT_COLUMNS: frozenset[str] = frozenset({"coverage_pct"})

# Adjusted OHLC prices: display rounded to 2 decimal places (presentation only).
PRICE_2DP_COLUMNS: frozenset[str] = frozenset(
    {
        "adj_open",
        "adj_high",
        "adj_low",
        "adj_close",
    }
)


def is_decimal_ratio_column(column: str) -> bool:
    """
    True when ``column`` stores a decimal ratio (0.05 = 5%) for display as percent.

    Prefer explicit definition-backed names; also accept ``return_*`` and ``*_pct``
    heuristics while excluding macro percentage-point fields.
    """
    if column in MACRO_PERCENTAGE_POINT_COLUMNS:
        return False
    if column in _ALREADY_PERCENT_POINT_COLUMNS:
        return False
    if column in _EXPLICIT_DECIMAL_RATIO_COLUMNS:
        return True
    if column.startswith("return_"):
        return True
    if column.endswith("_pct"):
        return True
    return False


def format_percent_ratio(value: Any) -> str:
    """Display-only: decimal ratio → percent string with 2 d.p. (0.00697 → 0.70%)."""
    num = float(value)
    return f"{num * 100:.2f}%"


def is_price_2dp_column(column: str) -> bool:
    """True when ``column`` should round to 2 decimal places on screen (adj OHLC)."""
    return column in PRICE_2DP_COLUMNS


def format_price_2dp(value: Any) -> str:
    """Display-only: price → 2 decimal places (584.1333193 → 584.13)."""
    return f"{float(value):.2f}"


def format_cell(value: Any, *, column: str | None = None) -> str:
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
    if column and is_decimal_ratio_column(column) and isinstance(value, (int, float, Decimal)):
        return format_percent_ratio(value)
    if column and is_price_2dp_column(column) and isinstance(value, (int, float, Decimal)):
        return format_price_2dp(value)
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
    """Format row dicts for on-screen display only (does not mutate ``rows``)."""
    return [{k: format_cell(v, column=k) for k, v in row.items()} for row in rows]
