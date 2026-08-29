"""Validation for daily_market_data."""

from __future__ import annotations

import datetime as dt
import math

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from stockballdb.market_data.normalize import OBSERVED_COLUMNS
from stockballdb.market_data.universe import (
    CLOSE_ONLY_SYMBOLS,
    PHASE_2A_ETF_SYMBOLS,
    is_close_only_symbol,
)

CLOSE_ONLY_NULL_OBSERVED = (
    "open",
    "high",
    "low",
    "volume",
    "adj_open",
    "adj_high",
    "adj_low",
    "adj_close",
    "adj_volume",
    "dividend_cash",
    "split_factor",
)

FULL_OHLC_REQUIRED = (
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


class DailyMarketDataValidationError(Exception):
    """Raised when daily_market_data validation fails."""


def _validate_common_frame(
    frame: pd.DataFrame,
    *,
    trading_days: set[dt.date],
    required_symbols: tuple[str, ...],
) -> list[str]:
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

    return errors


def _validate_full_ohlc_symbol_frame(symbol_frame: pd.DataFrame, symbol: str) -> list[str]:
    errors: list[str] = []
    for col in FULL_OHLC_REQUIRED:
        series = symbol_frame[col]
        if series.isna().any():
            errors.append(f"{symbol}: null values in {col}")
        elif not all(math.isfinite(float(v)) for v in series):
            errors.append(f"{symbol}: non-finite values in {col}")

    if errors:
        return errors

    if (symbol_frame["volume"] < 0).any() or (symbol_frame["adj_volume"] < 0).any():
        errors.append(f"{symbol}: negative volume")

    bad_ohlc = symbol_frame[
        (symbol_frame["high"] < symbol_frame["low"])
        | (symbol_frame["high"] < symbol_frame["open"])
        | (symbol_frame["high"] < symbol_frame["close"])
        | (symbol_frame["low"] > symbol_frame["open"])
        | (symbol_frame["low"] > symbol_frame["close"])
    ]
    if not bad_ohlc.empty:
        row = bad_ohlc.iloc[0]
        errors.append(f"OHLC inconsistency for {row['symbol']} on {row['date']}")

    bad_adj = symbol_frame[
        (symbol_frame["adj_high"] < symbol_frame["adj_low"])
        | (symbol_frame["adj_high"] < symbol_frame["adj_open"])
        | (symbol_frame["adj_high"] < symbol_frame["adj_close"])
        | (symbol_frame["adj_low"] > symbol_frame["adj_open"])
        | (symbol_frame["adj_low"] > symbol_frame["adj_close"])
    ]
    if not bad_adj.empty:
        row = bad_adj.iloc[0]
        errors.append(
            f"adjusted OHLC inconsistency for {row['symbol']} on {row['date']}"
        )

    if (symbol_frame["split_factor"] <= 0).any():
        errors.append(f"{symbol}: split_factor must be > 0")

    if (symbol_frame["dividend_cash"] < 0).any():
        errors.append(f"{symbol}: dividend_cash must be >= 0")

    return errors


def _validate_close_only_symbol_frame(symbol_frame: pd.DataFrame, symbol: str) -> list[str]:
    errors: list[str] = []
    close = symbol_frame["close"]
    if close.isna().any():
        errors.append(f"{symbol}: close must be non-NULL")
    elif not all(math.isfinite(float(v)) for v in close):
        errors.append(f"{symbol}: non-finite close values")

    for col in CLOSE_ONLY_NULL_OBSERVED:
        if symbol_frame[col].notna().any():
            errors.append(f"{symbol}: {col} must be NULL for close-only rows")

    return errors


def validate_daily_market_data_frame(
    frame: pd.DataFrame,
    *,
    trading_days: set[dt.date],
    required_symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
) -> None:
    """Validate observed columns of a daily_market_data DataFrame."""
    errors = _validate_common_frame(
        frame,
        trading_days=trading_days,
        required_symbols=required_symbols,
    )

    for symbol, group in frame.groupby("symbol"):
        sym = str(symbol)
        if is_close_only_symbol(sym):
            errors.extend(_validate_close_only_symbol_frame(group, sym))
        else:
            errors.extend(_validate_full_ohlc_symbol_frame(group, sym))

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
        sym = str(symbol)
        g = group.sort_values("date")
        close_only = is_close_only_symbol(sym)

        if pd.notna(g["return_1d"].iloc[0]) or pd.notna(g["gap_pct"].iloc[0]):
            errors.append(
                f"{symbol}: first row must have NULL return_1d and gap_pct"
            )

        if close_only:
            if g["return_1d"].iloc[1:].isna().any():
                errors.append(f"{symbol}: return_1d must be non-NULL after first row")
            if g["gap_pct"].notna().any():
                errors.append(f"{symbol}: gap_pct must remain NULL for close-only")
            if g["intraday_return"].notna().any() or g["range_pct"].notna().any():
                errors.append(
                    f"{symbol}: intraday_return/range_pct must be NULL for close-only"
                )
        else:
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
    symbol_scope: str | None = None,
) -> None:
    """Validate persisted daily_market_data rows."""
    errors: list[str] = []
    with engine.connect() as conn:
        if symbol_scope:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM daily_market_data WHERE symbol = :symbol"
                ),
                {"symbol": symbol_scope},
            ).scalar_one()
        else:
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

        malformed_etf = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM daily_market_data
                WHERE symbol <> ALL(:close_only)
                  AND (
                    open IS NULL OR high IS NULL OR low IS NULL OR volume IS NULL
                    OR adj_open IS NULL OR adj_high IS NULL OR adj_low IS NULL
                    OR adj_close IS NULL OR adj_volume IS NULL
                    OR dividend_cash IS NULL OR split_factor IS NULL
                  )
                """
            ),
            {"close_only": list(CLOSE_ONLY_SYMBOLS)},
        ).scalar_one()
        if malformed_etf:
            errors.append(
                f"ETF rows missing required OHLC/adj/corp-action fields: {malformed_etf}"
            )

        malformed_close = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM daily_market_data
                WHERE symbol = ANY(:close_only)
                  AND (
                    open IS NOT NULL OR high IS NOT NULL OR low IS NOT NULL
                    OR volume IS NOT NULL OR adj_open IS NOT NULL OR adj_high IS NOT NULL
                    OR adj_low IS NOT NULL OR adj_close IS NOT NULL OR adj_volume IS NOT NULL
                    OR dividend_cash IS NOT NULL OR split_factor IS NOT NULL
                    OR close IS NULL
                  )
                """
            ),
            {"close_only": list(CLOSE_ONLY_SYMBOLS)},
        ).scalar_one()
        if malformed_close:
            errors.append(
                f"close-only rows with non-NULL OHLC/adj/corp-action: {malformed_close}"
            )

        if require_derived:
            scope_sql = " AND symbol = :symbol_scope" if symbol_scope else ""
            scope_params = {"symbol_scope": symbol_scope} if symbol_scope else {}

            if symbol_scope:
                symbol_count = 1
                null_ret = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM daily_market_data "
                        f"WHERE return_1d IS NULL{scope_sql}"
                    ),
                    scope_params,
                ).scalar_one()
            else:
                symbol_count = conn.execute(
                    text("SELECT COUNT(DISTINCT symbol) FROM daily_market_data")
                ).scalar_one()
                null_ret = conn.execute(
                    text("SELECT COUNT(*) FROM daily_market_data WHERE return_1d IS NULL")
                ).scalar_one()
            if null_ret != symbol_count:
                errors.append(
                    f"expected {symbol_count} NULL return_1d (first row per symbol); "
                    f"got return_1d_null={null_ret}"
                )

            if symbol_scope and is_close_only_symbol(symbol_scope):
                close_only_gap_set = conn.execute(
                    text(
                        f"""
                        SELECT COUNT(*) FROM daily_market_data
                        WHERE symbol = :symbol_scope AND gap_pct IS NOT NULL
                        """
                    ),
                    scope_params,
                ).scalar_one()
                if close_only_gap_set:
                    errors.append(
                        f"close-only symbols must have NULL gap_pct; found {close_only_gap_set}"
                    )
                close_only_intraday_set = conn.execute(
                    text(
                        f"""
                        SELECT COUNT(*) FROM daily_market_data
                        WHERE symbol = :symbol_scope
                          AND (intraday_return IS NOT NULL OR range_pct IS NOT NULL)
                        """
                    ),
                    scope_params,
                ).scalar_one()
                if close_only_intraday_set:
                    errors.append(
                        "close-only intraday_return/range_pct must remain NULL"
                    )
            elif not symbol_scope:
                etf_gap_null = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM daily_market_data
                        WHERE symbol <> ALL(:close_only) AND gap_pct IS NULL
                        """
                    ),
                    {"close_only": list(CLOSE_ONLY_SYMBOLS)},
                ).scalar_one()
                if etf_gap_null != len(PHASE_2A_ETF_SYMBOLS):
                    errors.append(
                        f"expected {len(PHASE_2A_ETF_SYMBOLS)} ETF NULL gap_pct "
                        f"(first row only); got {etf_gap_null}"
                    )

                close_only_gap_set = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM daily_market_data
                        WHERE symbol = ANY(:close_only) AND gap_pct IS NOT NULL
                        """
                    ),
                    {"close_only": list(CLOSE_ONLY_SYMBOLS)},
                ).scalar_one()
                if close_only_gap_set:
                    errors.append(
                        f"close-only symbols must have NULL gap_pct; found {close_only_gap_set}"
                    )

                etf_intraday_null = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM daily_market_data
                        WHERE symbol <> ALL(:close_only)
                          AND (intraday_return IS NULL OR range_pct IS NULL)
                        """
                    ),
                    {"close_only": list(CLOSE_ONLY_SYMBOLS)},
                ).scalar_one()
                if etf_intraday_null:
                    errors.append(
                        f"ETF intraday_return/range_pct unexpected NULLs: {etf_intraday_null}"
                    )

                close_only_intraday_set = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM daily_market_data
                        WHERE symbol = ANY(:close_only)
                          AND (intraday_return IS NOT NULL OR range_pct IS NOT NULL)
                        """
                    ),
                    {"close_only": list(CLOSE_ONLY_SYMBOLS)},
                ).scalar_one()
                if close_only_intraday_set:
                    errors.append(
                        "close-only intraday_return/range_pct must remain NULL"
                    )

            null_dd = conn.execute(
                text(
                    "SELECT COUNT(*) FROM daily_market_data "
                    f"WHERE drawdown_from_high IS NULL{scope_sql}"
                ),
                scope_params,
            ).scalar_one()
            if null_dd:
                errors.append(f"drawdown_from_high has {null_dd} unexpected NULLs")

    if errors:
        raise DailyMarketDataValidationError("; ".join(errors))
