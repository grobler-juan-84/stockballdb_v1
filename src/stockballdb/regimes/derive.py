"""Derive point-in-time asset_regimes from canonical daily_market_data."""

from __future__ import annotations

import math
from bisect import bisect_right, insort

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from stockballdb.market_data.universe import (
    PHASE_2A_ETF_SYMBOLS,
    asset_type_for_symbol,
    is_close_only_symbol,
)
from stockballdb.models.asset_regimes import AssetRegime

REGIME_COLUMNS = (
    "asset_type",
    "return_5d",
    "return_20d",
    "return_60d",
    "above_20dma",
    "above_50dma",
    "above_200dma",
    "distance_20dma_pct",
    "distance_50dma_pct",
    "distance_200dma_pct",
    "volatility_20d",
    "drawdown_pct",
    "trend_regime",
    "momentum_regime",
    "volatility_regime",
)

VOL_WINDOW = 20
VOL_ANNUALIZATION = math.sqrt(252)
VOL_REGIME_MIN_OBS = 252


class AssetRegimesValidationError(Exception):
    """Raised when asset_regimes validation fails."""


def _nan_to_none(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _bool_gt(price: pd.Series, sma: pd.Series) -> list[bool | None]:
    out: list[bool | None] = []
    for p, s in zip(price, sma):
        if pd.isna(s) or pd.isna(p):
            out.append(None)
        else:
            out.append(bool(p > s))
    return out


def _trend_regime(price: pd.Series, sma50: pd.Series, sma200: pd.Series) -> list[str | None]:
    out: list[str | None] = []
    for p, s50, s200 in zip(price, sma50, sma200):
        if pd.isna(s50) or pd.isna(s200) or pd.isna(p):
            out.append(None)
        elif p > s200 and s50 > s200:
            out.append("uptrend")
        elif p < s200 and s50 < s200:
            out.append("downtrend")
        else:
            out.append("neutral")
    return out


def _momentum_regime(r20: pd.Series, r60: pd.Series) -> list[str | None]:
    out: list[str | None] = []
    for a, b in zip(r20, r60):
        if pd.isna(a) or pd.isna(b):
            out.append(None)
        elif a > 0 and b > 0:
            out.append("positive")
        elif a < 0 and b < 0:
            out.append("negative")
        else:
            out.append("mixed")
    return out


def _expanding_volatility_regime(vol: pd.Series) -> list[str | None]:
    """Classify using expanding same-symbol empirical CDF through t (inclusive)."""
    hist: list[float] = []
    out: list[str | None] = []
    for v in vol:
        if pd.isna(v):
            out.append(None)
            continue
        fv = float(v)
        insort(hist, fv)
        n = len(hist)
        if n < VOL_REGIME_MIN_OBS:
            out.append(None)
            continue
        p = bisect_right(hist, fv) / n
        if p <= 1.0 / 3.0:
            out.append("low")
        elif p <= 2.0 / 3.0:
            out.append("normal")
        else:
            out.append("high")
    return out


def derive_asset_regimes(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Compute asset_regimes from daily_market_data columns available through date t.

    Requires: date, symbol, adj_close, return_1d, drawdown_from_high.
    """
    required = {"date", "symbol", "adj_close", "return_1d", "drawdown_from_high"}
    missing = required - set(frame.columns)
    if missing:
        raise AssetRegimesValidationError(
            f"asset_regimes derive missing columns: {sorted(missing)}"
        )
    if frame.empty:
        out = frame.copy()
        for col in REGIME_COLUMNS:
            out[col] = pd.Series(dtype="object")
        return out

    ordered = frame.sort_values(["symbol", "date"]).copy()
    parts: list[pd.DataFrame] = []

    for symbol, group in ordered.groupby("symbol", sort=False):
        g = group.copy().reset_index(drop=True)
        sym = str(symbol)
        if is_close_only_symbol(sym):
            adj = pd.to_numeric(g["close"], errors="coerce")
        else:
            adj = pd.to_numeric(g["adj_close"], errors="coerce")
        r1 = pd.to_numeric(g["return_1d"], errors="coerce")

        g["asset_type"] = asset_type_for_symbol(sym)

        for n in (5, 20, 60):
            prior = adj.shift(n)
            g[f"return_{n}d"] = (adj / prior - 1.0).where(prior.notna())

        sma20 = adj.rolling(20, min_periods=20).mean()
        sma50 = adj.rolling(50, min_periods=50).mean()
        sma200 = adj.rolling(200, min_periods=200).mean()

        g["above_20dma"] = _bool_gt(adj, sma20)
        g["above_50dma"] = _bool_gt(adj, sma50)
        g["above_200dma"] = _bool_gt(adj, sma200)

        g["distance_20dma_pct"] = (adj / sma20 - 1.0).where(sma20.notna())
        g["distance_50dma_pct"] = (adj / sma50 - 1.0).where(sma50.notna())
        g["distance_200dma_pct"] = (adj / sma200 - 1.0).where(sma200.notna())

        # Sample std (ddof=1) of 20 returns ending on t, annualized.
        vol_daily = r1.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=1)
        g["volatility_20d"] = (vol_daily * VOL_ANNUALIZATION).where(vol_daily.notna())

        # Deliberate mirror of daily_market_data.drawdown_from_high.
        g["drawdown_pct"] = pd.to_numeric(g["drawdown_from_high"], errors="coerce")

        g["trend_regime"] = _trend_regime(adj, sma50, sma200)
        g["momentum_regime"] = _momentum_regime(g["return_20d"], g["return_60d"])
        g["volatility_regime"] = _expanding_volatility_regime(g["volatility_20d"])

        parts.append(g)

    return pd.concat(parts, ignore_index=True)


def load_daily_market_for_regimes(
    engine: Engine,
    *,
    symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
) -> pd.DataFrame:
    """Load columns needed for asset_regimes derivation (no market_outcomes)."""
    placeholders = ", ".join(f":s{i}" for i in range(len(symbols)))
    params = {f"s{i}": s for i, s in enumerate(symbols)}
    sql = (
        "SELECT date, symbol, close, adj_close, return_1d, drawdown_from_high "
        "FROM daily_market_data "
        f"WHERE symbol IN ({placeholders}) ORDER BY symbol, date"
    )
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    if not rows:
        raise AssetRegimesValidationError(
            "daily_market_data has no rows for regime derivation"
        )
    frame = pd.DataFrame(rows)
    for col in ("close", "adj_close", "return_1d", "drawdown_from_high"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def upsert_asset_regimes(
    engine: Engine,
    frame: pd.DataFrame,
    *,
    batch_size: int = 400,
) -> int:
    """Idempotent upsert of asset_regimes rows."""
    if frame.empty:
        return 0

    cols = ["date", "symbol", *REGIME_COLUMNS]
    records = frame[cols].to_dict(orient="records")
    for rec in records:
        for col in REGIME_COLUMNS:
            rec[col] = _nan_to_none(rec[col])

    with engine.begin() as conn:
        for offset in range(0, len(records), batch_size):
            batch = records[offset : offset + batch_size]
            stmt = insert(AssetRegime).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[AssetRegime.date, AssetRegime.symbol],
                set_={col: getattr(stmt.excluded, col) for col in REGIME_COLUMNS},
            )
            conn.execute(stmt)
    return len(records)


def sync_asset_regimes(
    engine: Engine,
    *,
    symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
) -> pd.DataFrame:
    """Load daily_market_data, derive asset_regimes, upsert."""
    source = load_daily_market_for_regimes(engine, symbols=symbols)
    derived = derive_asset_regimes(source)
    upsert_asset_regimes(engine, derived)
    return derived
