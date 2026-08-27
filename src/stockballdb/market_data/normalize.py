"""Normalize Tiingo EOD bars into canonical daily_market_data rows."""

from __future__ import annotations

import datetime as dt
import math
from typing import Any

import pandas as pd

OBSERVED_COLUMNS = (
    "date",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adj_open",
    "adj_high",
    "adj_low",
    "adj_close",
    "adj_volume",
    "dividend_cash",
    "split_factor",
)


def _parse_date(value: Any) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    text = str(value)
    # Tiingo: "2024-01-02T00:00:00.000Z"
    if "T" in text:
        text = text.split("T", 1)[0]
    return dt.date.fromisoformat(text)


def _require_number(row: dict, key: str, *, symbol: str) -> float:
    if key not in row or row[key] is None:
        raise ValueError(f"{symbol}: missing Tiingo field {key}")
    try:
        number = float(row[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{symbol}: invalid numeric {key}={row[key]!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{symbol}: non-finite {key}={row[key]!r}")
    return number


def normalize_tiingo_bars(
    symbol: str,
    bars: list[dict],
    *,
    trading_days: set[dt.date],
) -> pd.DataFrame:
    """
    Map Tiingo bars to canonical observed columns.

    Rows whose date is not in ``trading_days`` are dropped (counted by caller
    via returned frame vs input length). Derived fields are not computed.
    """
    symbol = symbol.upper()
    records: list[dict] = []
    outside: list[dt.date] = []

    for bar in bars:
        session_date = _parse_date(bar["date"])
        if session_date not in trading_days:
            outside.append(session_date)
            continue

        records.append(
            {
                "date": session_date,
                "symbol": symbol,
                "open": _require_number(bar, "open", symbol=symbol),
                "high": _require_number(bar, "high", symbol=symbol),
                "low": _require_number(bar, "low", symbol=symbol),
                "close": _require_number(bar, "close", symbol=symbol),
                "volume": int(_require_number(bar, "volume", symbol=symbol)),
                "adj_open": _require_number(bar, "adjOpen", symbol=symbol),
                "adj_high": _require_number(bar, "adjHigh", symbol=symbol),
                "adj_low": _require_number(bar, "adjLow", symbol=symbol),
                "adj_close": _require_number(bar, "adjClose", symbol=symbol),
                "adj_volume": int(_require_number(bar, "adjVolume", symbol=symbol)),
                # Store Tiingo values as observed (typically 0.0 / 1.0 on quiet days).
                "dividend_cash": _require_number(bar, "divCash", symbol=symbol),
                "split_factor": _require_number(bar, "splitFactor", symbol=symbol),
            }
        )

    frame = pd.DataFrame.from_records(records, columns=list(OBSERVED_COLUMNS))
    if frame.empty:
        return frame

    frame = frame.sort_values(["symbol", "date"]).reset_index(drop=True)
    frame.attrs["tiingo_dates_outside_trading_days"] = outside
    return frame
