"""Derive retrospective market_outcomes from canonical daily_market_data."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS
from stockballdb.models.market_outcomes import MarketOutcome

OUTCOME_COLUMNS = (
    "return_1d",
    "return_3d",
    "return_5d",
    "return_10d",
    "return_20d",
    "max_up_5d",
    "max_down_5d",
    "max_up_20d",
    "max_down_20d",
    "positive_1d",
    "positive_5d",
    "positive_20d",
)

RETURN_HORIZONS = (1, 3, 5, 10, 20)
MAX_HORIZONS = (5, 20)


class MarketOutcomesValidationError(Exception):
    """Raised when market_outcomes validation fails."""


def _nan_to_none(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pd.isna(value):
        return None
    return value


def derive_market_outcomes(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Compute market_outcomes fields from observed daily_market_data columns.

    Requires columns: date, symbol, adj_close, adj_high, adj_low.
    Per-symbol, ordered by date. Incomplete horizons → NULL.
    """
    required = {"date", "symbol", "adj_close", "adj_high", "adj_low"}
    missing = required - set(frame.columns)
    if missing:
        raise MarketOutcomesValidationError(
            f"outcomes derive missing columns: {sorted(missing)}"
        )
    if frame.empty:
        out = frame.copy()
        for col in OUTCOME_COLUMNS:
            out[col] = pd.Series(dtype="object")
        return out

    ordered = frame.sort_values(["symbol", "date"]).copy()
    parts: list[pd.DataFrame] = []

    for _symbol, group in ordered.groupby("symbol", sort=False):
        g = group.copy().reset_index(drop=True)
        base = g["adj_close"]

        for n in RETURN_HORIZONS:
            future = base.shift(-n)
            complete = future.notna()
            g[f"return_{n}d"] = (future / base - 1.0).where(complete)

        for n in MAX_HORIZONS:
            highs = pd.concat(
                [g["adj_high"].shift(-i) for i in range(1, n + 1)],
                axis=1,
            )
            lows = pd.concat(
                [g["adj_low"].shift(-i) for i in range(1, n + 1)],
                axis=1,
            )
            complete = highs.notna().all(axis=1) & lows.notna().all(axis=1)
            g[f"max_up_{n}d"] = (highs.max(axis=1) / base - 1.0).where(complete)
            g[f"max_down_{n}d"] = (lows.min(axis=1) / base - 1.0).where(complete)

        for n in (1, 5, 20):
            ret = g[f"return_{n}d"]
            flags: list[bool | None] = []
            for v in ret:
                if pd.isna(v):
                    flags.append(None)
                else:
                    flags.append(bool(v > 0))
            g[f"positive_{n}d"] = flags

        parts.append(g)

    return pd.concat(parts, ignore_index=True)


def load_daily_market_for_outcomes(
    engine: Engine,
    *,
    symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
) -> pd.DataFrame:
    """Load price columns needed for outcome derivation."""
    placeholders = ", ".join(f":s{i}" for i in range(len(symbols)))
    params = {f"s{i}": s for i, s in enumerate(symbols)}
    sql = (
        "SELECT date, symbol, adj_close, adj_high, adj_low "
        "FROM daily_market_data "
        f"WHERE symbol IN ({placeholders}) ORDER BY symbol, date"
    )
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    if not rows:
        raise MarketOutcomesValidationError(
            "daily_market_data has no rows for outcome derivation"
        )
    frame = pd.DataFrame(rows)
    for col in ("adj_close", "adj_high", "adj_low"):
        frame[col] = pd.to_numeric(frame[col])
    return frame


def upsert_market_outcomes(
    engine: Engine,
    frame: pd.DataFrame,
    *,
    batch_size: int = 500,
) -> int:
    """Idempotent upsert of market_outcomes rows."""
    if frame.empty:
        return 0

    cols = ["date", "symbol", *OUTCOME_COLUMNS]
    records = frame[cols].to_dict(orient="records")
    for rec in records:
        for col in OUTCOME_COLUMNS:
            rec[col] = _nan_to_none(rec[col])

    with engine.begin() as conn:
        for offset in range(0, len(records), batch_size):
            batch = records[offset : offset + batch_size]
            stmt = insert(MarketOutcome).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[MarketOutcome.date, MarketOutcome.symbol],
                set_={col: getattr(stmt.excluded, col) for col in OUTCOME_COLUMNS},
            )
            conn.execute(stmt)
    return len(records)


def sync_market_outcomes(
    engine: Engine,
    *,
    symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
) -> pd.DataFrame:
    """Load daily_market_data, derive outcomes, upsert."""
    source = load_daily_market_for_outcomes(engine, symbols=symbols)
    derived = derive_market_outcomes(source)
    upsert_market_outcomes(engine, derived)
    return derived
