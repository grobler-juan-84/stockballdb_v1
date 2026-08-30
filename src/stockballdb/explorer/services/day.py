"""Day Inspector service."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.engine import Connection

from stockballdb.explorer.queries import (
    fetch_row_by_date,
    fetch_rows_for_date,
    fetch_scheduled_events_for_date,
    fetch_trading_day,
    nearest_trading_sessions,
)
from stockballdb.market_data.universe import V1_MARKET_SYMBOLS


@dataclass
class DayInspectorResult:
    calendar_date: dt.date
    is_trading_day: bool
    trading_day: dict[str, Any] | None
    calendar_context: dict[str, Any] | None
    scheduled_events: list[dict[str, Any]]
    macro_conditions: dict[str, Any] | None
    daily_market_data: list[dict[str, Any]]
    market_outcomes: list[dict[str, Any]]
    asset_regimes: list[dict[str, Any]]
    previous_session: dict[str, Any] | None
    next_session: dict[str, Any] | None
    symbol_filter: str | None = None
    messages: list[str] = field(default_factory=list)


def inspect_day(
    conn: Connection,
    calendar_date: dt.date,
    symbol: str | None = None,
) -> DayInspectorResult:
    messages: list[str] = []
    if symbol and symbol not in V1_MARKET_SYMBOLS:
        messages.append(f"Unknown symbol {symbol!r}; not in V1 universe.")

    trading = fetch_trading_day(conn, calendar_date)
    is_trading = trading is not None
    prev_sess, next_sess = nearest_trading_sessions(conn, calendar_date)

    if not is_trading:
        messages.append("Trading session: none on this calendar date.")
        if prev_sess:
            messages.append(
                f"Previous StockBallDB session: {prev_sess['date']}"
            )
        if next_sess:
            messages.append(f"Next StockBallDB session: {next_sess['date']}")

    events = fetch_scheduled_events_for_date(conn, calendar_date)
    calendar_ctx = fetch_row_by_date(conn, "calendar_context", calendar_date) if is_trading else None
    macro = fetch_row_by_date(conn, "macro_conditions", calendar_date) if is_trading else None

    dmd = fetch_rows_for_date(conn, "daily_market_data", calendar_date, symbol) if is_trading else []
    outcomes = fetch_rows_for_date(conn, "market_outcomes", calendar_date, symbol) if is_trading else []
    regimes = fetch_rows_for_date(conn, "asset_regimes", calendar_date, symbol) if is_trading else []

    return DayInspectorResult(
        calendar_date=calendar_date,
        is_trading_day=is_trading,
        trading_day=trading,
        calendar_context=calendar_ctx,
        scheduled_events=events,
        macro_conditions=macro,
        daily_market_data=dmd,
        market_outcomes=outcomes,
        asset_regimes=regimes,
        previous_session=prev_sess,
        next_session=next_sess,
        symbol_filter=symbol,
        messages=messages,
    )
