"""Canonical table registry for Explorer Data Explorer."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Callable

from stockballdb.events.types import EVENT_TYPES
from stockballdb.models.asset_regimes import AssetRegime
from stockballdb.models.calendar_context import CalendarContext
from stockballdb.models.daily_market_data import DailyMarketData
from stockballdb.models.macro_conditions import MacroCondition
from stockballdb.models.market_outcomes import MarketOutcome
from stockballdb.models.scheduled_events import ScheduledEvent
from stockballdb.models.trading_days import TradingDay


class ExplorerQueryError(Exception):
    """Invalid Explorer table query parameters."""


@dataclass(frozen=True)
class TableSpec:
    key: str
    display_name: str
    model: type
    date_column: str
    symbol_column: str | None
    default_sort: tuple[tuple[str, str], ...]
    sortable_columns: frozenset[str]
    boolean_filter_columns: frozenset[str] = frozenset()
    event_type_filter: bool = False


def _symbol_date_sort() -> tuple[tuple[str, str], ...]:
    return (("date", "asc"), ("symbol", "asc"))


TABLE_REGISTRY: dict[str, TableSpec] = {
    "trading_days": TableSpec(
        key="trading_days",
        display_name="Trading Days",
        model=TradingDay,
        date_column="date",
        symbol_column=None,
        default_sort=(("date", "asc"),),
        sortable_columns=frozenset({"date", "year", "month", "weekday"}),
    ),
    "daily_market_data": TableSpec(
        key="daily_market_data",
        display_name="Daily Market Data",
        model=DailyMarketData,
        date_column="date",
        symbol_column="symbol",
        default_sort=_symbol_date_sort(),
        sortable_columns=frozenset({"date", "symbol", "close", "adj_close", "volume"}),
    ),
    "market_outcomes": TableSpec(
        key="market_outcomes",
        display_name="Market Outcomes",
        model=MarketOutcome,
        date_column="date",
        symbol_column="symbol",
        default_sort=_symbol_date_sort(),
        sortable_columns=frozenset({"date", "symbol", "return_1d", "return_5d", "return_20d"}),
    ),
    "asset_regimes": TableSpec(
        key="asset_regimes",
        display_name="Asset Regimes",
        model=AssetRegime,
        date_column="date",
        symbol_column="symbol",
        default_sort=_symbol_date_sort(),
        sortable_columns=frozenset(
            {"date", "symbol", "trend_regime", "momentum_regime", "volatility_regime"}
        ),
    ),
    "macro_conditions": TableSpec(
        key="macro_conditions",
        display_name="Macro Conditions",
        model=MacroCondition,
        date_column="date",
        symbol_column=None,
        default_sort=(("date", "asc"),),
        sortable_columns=frozenset(
            {"date", "inflation_rate", "unemployment_rate", "fed_funds_rate"}
        ),
    ),
    "scheduled_events": TableSpec(
        key="scheduled_events",
        display_name="Scheduled Events",
        model=ScheduledEvent,
        date_column="event_date",
        symbol_column="symbol",
        default_sort=(("event_date", "asc"), ("event_id", "asc")),
        sortable_columns=frozenset(
            {"event_date", "event_id", "event_type", "symbol", "reference_period"}
        ),
        event_type_filter=True,
    ),
    "calendar_context": TableSpec(
        key="calendar_context",
        display_name="Calendar Context",
        model=CalendarContext,
        date_column="date",
        symbol_column=None,
        default_sort=(("date", "asc"),),
        sortable_columns=frozenset({"date"}),
        boolean_filter_columns=frozenset(
            {
                "is_day_before_holiday",
                "is_day_after_holiday",
                "is_shortened_trading_day",
                "is_fomc_day",
                "is_cpi_release_day",
                "is_employment_situation_day",
                "is_election_day",
                "is_turn_of_month",
                "is_quarter_transition",
                "is_year_transition",
            }
        ),
    ),
}


def get_table_spec(table_key: str) -> TableSpec:
    if table_key not in TABLE_REGISTRY:
        raise ExplorerQueryError(f"unknown table: {table_key!r}")
    return TABLE_REGISTRY[table_key]


def list_table_keys() -> list[str]:
    return list(TABLE_REGISTRY.keys())


def allowed_event_types() -> tuple[str, ...]:
    return tuple(sorted(EVENT_TYPES))
