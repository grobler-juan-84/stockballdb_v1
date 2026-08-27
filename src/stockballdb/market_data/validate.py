"""Validation for daily_market_data."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from stockballdb.market_data.normalize import OBSERVED_COLUMNS
from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS


class DailyMarketDataValidationError(Exception):
    """Raised when daily_market_data validation fails."""


def validate_daily_market_data_frame(
    frame: pd.DataFrame,
    *,
    trading_days: set[dt.date],
    required_symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
) -> None:
    """Validate observed columns of a daily_market_data DataFrame."""
    errors: list[str] = []

    if frame.empty:
        raise DailyMarketDataValidationError("daily_market_data frame is empty")

    missing_cols = [c for c in OBSERVED_COLUMNS if c not in frame.columns]
    if missing_cols:
        errors.append(f"missing columns: {missing_cols}")

    if frame.duplicated(subset=["date", "symbol"]).any():
        errors.append("duplicate (date, symbol) rows")

    symbols_present = set(frame["symbol"].unique())
    missing_symbols = [s for s in required_symbols if s not in symbols_present]
    if missing_symbols:
        errors.append(f"missing required symbols: {missing_symbols}")

    unexpected = symbols_present - set(required_symbols)
    if unexpected:
        errors.append(f"unexpected symbols: {sorted(unexpected)}")

    outside = [d for d in frame["date"] if d not in trading_days]
    if outside:
        errors.append(
            f"{len(outside)} rows have dates not in trading_days "
            f"(example={outside[0]})"
        )

    weekends = [d for d in frame["date"] if d.isoweekday() > 5]
    if weekends:
        errors.append(f"weekend dates present: {weekends[0]}")

    for col in (
        "open",
        "high",
        "low",
        "close",
        "adj_open",
        "adj_high",
        "adj_low",
        "adj_close",
        "dividend_cash",
        "split_factor",
    ):
        series = frame[col]
        if series.isna().any():
            errors.append(f"null values in {col}")
        elif not all(math.isfinite(float(v)) for v in series):
            errors.append(f"non-finite values in {col}")

    if (frame["volume"] < 0).any() or (frame["adj_volume"] < 0).any():
        errors.append("negative volume")

    bad_ohlc = frame[
        (frame["high"] < frame["low"])
        | (frame["high"] < frame["open"])
        | (frame["high"] < frame["close"])
        | (frame["low"] > frame["open"])
        | (frame["low"] > frame["close"])
    ]
    if not bad_ohlc.empty:
        row = bad_ohlc.iloc[0]
        errors.append(
            f"OHLC inconsistency for {row['symbol']} on {row['date']}"
        )

    bad_adj = frame[
        (frame["adj_high"] < frame["adj_low"])
        | (frame["adj_high"] < frame["adj_open"])
        | (frame["adj_high"] < frame["adj_close"])
        | (frame["adj_low"] > frame["adj_open"])
        | (frame["adj_low"] > frame["adj_close"])
    ]
    if not bad_adj.empty:
        row = bad_adj.iloc[0]
        errors.append(
            f"adjusted OHLC inconsistency for {row['symbol']} on {row['date']}"
        )

    if (frame["split_factor"] <= 0).any():
        errors.append("split_factor must be > 0")

    if (frame["dividend_cash"] < 0).any():
        errors.append("dividend_cash must be >= 0")

    if errors:
        raise DailyMarketDataValidationError("; ".join(errors))


def validate_derived_market_data_frame(frame: pd.DataFrame) -> None:
    """Validate Phase 2B derived columns on a per-symbol ordered frame."""
    errors: list[str] = []
    required = (
        "return_1d",
        "gap_pct",
        "intraday_return",
        "range_pct",
        "drawdown_from_high",
    )
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise DailyMarketDataValidationError(
            f"derived frame missing columns: {missing}"
        )

    for symbol, group in frame.groupby("symbol"):
        g = group.sort_values("date")
        if pd.notna(g["return_1d"].iloc[0]) or pd.notna(g["gap_pct"].iloc[0]):
            errors.append(
                f"{symbol}: first row must have NULL return_1d and gap_pct"
            )
        if g["return_1d"].iloc[1:].isna().any() or g["gap_pct"].iloc[1:].isna().any():
            errors.append(
                f"{symbol}: return_1d/gap_pct must be non-NULL after first row"
            )
        if g["intraday_return"].isna().any() or g["range_pct"].isna().any():
            errors.append(
                f"{symbol}: intraday_return/range_pct must be non-NULL on all rows"
            )
        if g["drawdown_from_high"].isna().any():
            errors.append(
                f"{symbol}: drawdown_from_high must be non-NULL on all rows"
            )
        if abs(float(g["drawdown_from_high"].iloc[0])) > 1e-12:
            errors.append(
                f"{symbol}: first-row drawdown_from_high must be 0"
            )

    if errors:
        raise DailyMarketDataValidationError("; ".join(errors))


def validate_daily_market_data_db(
    engine: Engine,
    *,
    expected_count: int,
    required_symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
    require_derived: bool = False,
) -> None:
    """Validate persisted daily_market_data rows."""
    errors: list[str] = []
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM daily_market_data")
        ).scalar_one()
        if count != expected_count:
            errors.append(f"row count {count} != expected {expected_count}")

        dupes = conn.execute(
            text(
                "SELECT COUNT(*) FROM ("
                "SELECT date, symbol FROM daily_market_data "
                "GROUP BY date, symbol HAVING COUNT(*) > 1"
                ") d"
            )
        ).scalar_one()
        if dupes:
            errors.append("duplicate primary keys in database")

        orphan = conn.execute(
            text(
                "SELECT COUNT(*) FROM daily_market_data d "
                "WHERE NOT EXISTS ("
                "SELECT 1 FROM trading_days t WHERE t.date = d.date"
                ")"
            )
        ).scalar_one()
        if orphan:
            errors.append(f"orphan dates not in trading_days: {orphan}")

        for symbol in required_symbols:
            n = conn.execute(
                text(
                    "SELECT COUNT(*) FROM daily_market_data WHERE symbol = :symbol"
                ),
                {"symbol": symbol},
            ).scalar_one()
            if n < 1:
                errors.append(f"no rows for symbol {symbol}")

        if require_derived:
            symbol_count = conn.execute(
                text("SELECT COUNT(DISTINCT symbol) FROM daily_market_data")
            ).scalar_one()
            null_ret = conn.execute(
                text("SELECT COUNT(*) FROM daily_market_data WHERE return_1d IS NULL")
            ).scalar_one()
            null_gap = conn.execute(
                text("SELECT COUNT(*) FROM daily_market_data WHERE gap_pct IS NULL")
            ).scalar_one()
            if null_ret != symbol_count or null_gap != symbol_count:
                errors.append(
                    f"expected {symbol_count} NULL return_1d/gap_pct "
                    f"(first row per symbol); got return_1d_null={null_ret} "
                    f"gap_pct_null={null_gap}"
                )
            for col in ("intraday_return", "range_pct", "drawdown_from_high"):
                nn = conn.execute(
                    text(
                        f"SELECT COUNT(*) FROM daily_market_data WHERE {col} IS NULL"
                    )
                ).scalar_one()
                if nn:
                    errors.append(f"{col} has {nn} unexpected NULLs")

    if errors:
        raise DailyMarketDataValidationError("; ".join(errors))
