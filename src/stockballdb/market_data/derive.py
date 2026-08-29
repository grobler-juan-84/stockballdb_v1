"""Derive daily_market_data behavioral fields from canonical observations."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from stockballdb.market_data.build import _sanitize_market_record
from stockballdb.market_data.normalize import OBSERVED_COLUMNS
from stockballdb.market_data.universe import (
    PHASE_2A_ETF_SYMBOLS,
    is_close_only_symbol,
)
from stockballdb.market_data.validate import DailyMarketDataValidationError
from stockballdb.models.daily_market_data import DailyMarketData

DERIVED_COLUMNS = (
    "return_1d",
    "gap_pct",
    "intraday_return",
    "range_pct",
    "drawdown_from_high",
)


def _derive_full_ohlc_group(g: pd.DataFrame) -> pd.DataFrame:
    prev_adj_close = g["adj_close"].shift(1)
    g["return_1d"] = g["adj_close"] / prev_adj_close - 1.0
    g["gap_pct"] = g["adj_open"] / prev_adj_close - 1.0
    g["intraday_return"] = g["close"] / g["open"] - 1.0
    g["range_pct"] = (g["high"] - g["low"]) / g["open"]
    hist_high = g["adj_close"].cummax()
    g["drawdown_from_high"] = g["adj_close"] / hist_high - 1.0
    return g


def _derive_close_only_group(g: pd.DataFrame) -> pd.DataFrame:
    prev_close = g["close"].shift(1)
    g["return_1d"] = g["close"] / prev_close - 1.0
    g["gap_pct"] = pd.NA
    g["intraday_return"] = pd.NA
    g["range_pct"] = pd.NA
    hist_high = g["close"].cummax()
    g["drawdown_from_high"] = g["close"] / hist_high - 1.0
    return g


def derive_daily_market_fields(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Phase 2B derived columns from canonical observed columns.

    Operates per symbol ordered by ``date``. Does not call any provider API.
    """
    required = set(OBSERVED_COLUMNS)
    missing = required - set(frame.columns)
    if missing:
        raise DailyMarketDataValidationError(
            f"derive requires observed columns missing: {sorted(missing)}"
        )
    if frame.empty:
        out = frame.copy()
        for col in DERIVED_COLUMNS:
            out[col] = pd.Series(dtype="float64")
        return out

    out = frame.sort_values(["symbol", "date"]).copy()
    parts: list[pd.DataFrame] = []
    for symbol, group in out.groupby("symbol", sort=False):
        g = group.copy()
        if is_close_only_symbol(str(symbol)):
            parts.append(_derive_close_only_group(g))
        else:
            parts.append(_derive_full_ohlc_group(g))

    return pd.concat(parts, ignore_index=True)


def load_observed_market_data(
    engine: Engine,
    *,
    symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
) -> pd.DataFrame:
    """Load canonical observed columns from PostgreSQL."""
    placeholders = ", ".join(f":s{i}" for i in range(len(symbols)))
    params = {f"s{i}": s for i, s in enumerate(symbols)}
    cols = ", ".join(OBSERVED_COLUMNS)
    sql = (
        f"SELECT {cols} FROM daily_market_data "
        f"WHERE symbol IN ({placeholders}) ORDER BY symbol, date"
    )
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.mappings().all()
    if not rows:
        raise DailyMarketDataValidationError("daily_market_data has no rows to derive")
    frame = pd.DataFrame(rows)
    numeric_cols = [c for c in OBSERVED_COLUMNS if c not in ("date", "symbol")]
    for col in numeric_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def upsert_derived_market_data(
    engine: Engine,
    frame: pd.DataFrame,
    *,
    batch_size: int = 500,
) -> int:
    """
    Idempotently write derived columns only.

    On conflict, observed columns are left unchanged.
    """
    if frame.empty:
        return 0

    cols = list(OBSERVED_COLUMNS) + list(DERIVED_COLUMNS)
    records = frame[cols].to_dict(orient="records")
    for rec in records:
        _sanitize_market_record(rec)
        for col in DERIVED_COLUMNS:
            val = rec[col]
            if val is None or (isinstance(val, float) and pd.isna(val)):
                rec[col] = None
            else:
                rec[col] = float(val)

    with engine.begin() as conn:
        for offset in range(0, len(records), batch_size):
            batch = records[offset : offset + batch_size]
            stmt = insert(DailyMarketData).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[DailyMarketData.date, DailyMarketData.symbol],
                set_={col: getattr(stmt.excluded, col) for col in DERIVED_COLUMNS},
            )
            conn.execute(stmt)
    return len(records)


def sync_derived_market_data(
    engine: Engine,
    *,
    symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
) -> pd.DataFrame:
    """Load observations, derive fields, upsert derived columns, return frame."""
    observed = load_observed_market_data(engine, symbols=symbols)
    derived = derive_daily_market_fields(observed)
    upsert_derived_market_data(engine, derived)
    return derived


def derived_coverage_summary(engine: Engine) -> dict:
    """Return non-NULL counts for derived columns."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                  COUNT(*) AS rows,
                  COUNT(return_1d) AS return_1d_nn,
                  COUNT(gap_pct) AS gap_pct_nn,
                  COUNT(intraday_return) AS intraday_return_nn,
                  COUNT(range_pct) AS range_pct_nn,
                  COUNT(drawdown_from_high) AS drawdown_from_high_nn,
                  COUNT(DISTINCT symbol) AS symbols
                FROM daily_market_data
                """
            )
        ).mappings().one()
    return dict(row)
