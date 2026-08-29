"""Expected limitations registry — not health defects."""

from __future__ import annotations

import datetime as dt

from stockballdb.events.types import EVENT_TYPES
from stockballdb.macro.series import MACRO_SERIES

# Historical floors for macro fields (trading-day date of first non-null expectation).
MACRO_FIELD_FLOORS: dict[str, dt.date] = {
    "inflation_rate": dt.date(1972, 7, 21),
    "core_inflation_rate": dt.date(1996, 12, 12),
    "unemployment_rate": dt.date(1960, 3, 15),
    "jobless_claims": dt.date(2009, 5, 28),
    "fed_funds_rate": dt.date(1957, 1, 2),
    "treasury_2y_yield": dt.date(1976, 6, 1),
    "treasury_10y_yield": dt.date(1962, 1, 2),
    "yield_curve_10y_2y": dt.date(1976, 6, 1),
    "fed_balance_sheet": dt.date(2002, 12, 20),
    "credit_spread": dt.date(1986, 1, 2),
}

EVENT_FAMILY_FLOORS: dict[str, dt.date] = {
    "fomc": dt.date(1957, 1, 8),
    "cpi": dt.date(1972, 7, 21),
    "employment_situation": dt.date(1960, 3, 15),
    "election": dt.date(1958, 11, 4),
}

WTI_INCEPTION = dt.date(1986, 1, 2)

UNRESOLVED_SYMBOLS = ("XAU/USD", "DXY")
UNRESOLVED_MACRO = ("pmi",)

# Freshness thresholds (Phase 8A provisional).
ETF_LAG_INFO_MAX = 3
ETF_LAG_WARNING_MAX = 5
ETF_CONSECUTIVE_GAP_ERROR = 10
WTI_LAG_INFO_MAX = 3
WTI_LAG_WARNING_MAX = 5
SPINE_LAG_WARNING = 5

# Macro field staleness: max trading sessions since last non-null before WARNING.
MACRO_DAILY_STALE_SESSIONS = 5
MACRO_WEEKLY_STALE_SESSIONS = 10
MACRO_MONTHLY_STALE_SESSIONS = 45

MACRO_WEEKLY_FIELDS = frozenset({"jobless_claims"})
MACRO_MONTHLY_FIELDS = frozenset(
    {"inflation_rate", "core_inflation_rate", "unemployment_rate", "fed_balance_sheet"}
)

EXPECTED_LIMITATIONS: tuple[str, ...] = (
    "WTI begins 1986-01-02",
    "CPI scheduled events from ~1972 (ALFRED)",
    "Employment events from ~1960",
    "core CPI PIT from ~1996",
    "DGS2 from 1976-06-01",
    "BAA10Y from ~1986",
    "ICSA sparse pre-2009",
    "Per-symbol ETF inception dates",
    "PMI unresolved",
    "XAU/USD and DXY unresolved",
    "No raw snapshot archive (Phase 9)",
)

def macro_series_ids() -> dict[str, str]:
    return {s.field: s.series_id for s in MACRO_SERIES}

def event_type_list() -> tuple[str, ...]:
    return tuple(sorted(EVENT_TYPES))
