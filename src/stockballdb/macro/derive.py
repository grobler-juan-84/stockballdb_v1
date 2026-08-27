"""Derive macro_conditions frame from aligned series + regimes."""

from __future__ import annotations

import datetime as dt
from bisect import bisect_right

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from stockballdb.macro.series import (
    INFLATION_REGIME_MIN_RELEASES,
    RATE_REGIME_LOOKBACK,
    RATE_REGIME_THRESHOLD,
)
from stockballdb.models.macro_conditions import MacroCondition

MACRO_COLUMNS = (
    "inflation_rate",
    "core_inflation_rate",
    "unemployment_rate",
    "jobless_claims",
    "fed_funds_rate",
    "treasury_2y_yield",
    "treasury_10y_yield",
    "yield_curve_10y_2y",
    "fed_balance_sheet",
    "credit_spread",
    "inflation_regime",
    "rate_regime",
)


class MacroConditionsValidationError(Exception):
    """Raised when macro_conditions validation fails."""


def _nan_to_none(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def derive_yield_curve(frame: pd.DataFrame) -> pd.Series:
    t10 = pd.to_numeric(frame["treasury_10y_yield"], errors="coerce")
    t2 = pd.to_numeric(frame["treasury_2y_yield"], errors="coerce")
    # Round to avoid binary-float artifacts when persisting NUMERIC.
    return (t10 - t2).where(t10.notna() & t2.notna()).round(8)


def derive_rate_regime(fed_funds: pd.Series) -> list[str | None]:
    """Effective-rate stance proxy over 63 prior non-NULL trading-day observations."""
    out: list[str | None] = []
    history: list[float] = []
    for v in fed_funds:
        if pd.isna(v):
            out.append(None)
            continue
        fv = float(v)
        if len(history) < RATE_REGIME_LOOKBACK:
            out.append(None)
            history.append(fv)
            continue
        prior = history[-RATE_REGIME_LOOKBACK]
        delta = fv - prior
        if delta <= -RATE_REGIME_THRESHOLD:
            out.append("easing")
        elif delta >= RATE_REGIME_THRESHOLD:
            out.append("tightening")
        else:
            out.append("stable")
        history.append(fv)
    return out


def derive_inflation_regime(
    inflation_rate: pd.Series,
    distinct_releases: list[tuple[dt.date, float]],
    *,
    min_releases: int = INFLATION_REGIME_MIN_RELEASES,
) -> list[str | None]:
    """
    Expanding terciles over distinct PIT inflation releases (not daily duplicates).

    On date t, H_t = release YoYs with availability <= t (each release once).
    Current comparison value = inflation_rate_t (forward-filled latest reading).
    """
    release_days = [d for d, _ in distinct_releases]
    release_vals = [v for _, v in distinct_releases]
    out: list[str | None] = []

    def _as_date(d) -> dt.date:
        if isinstance(d, dt.datetime):
            return d.date()
        if isinstance(d, dt.date):
            return d
        if hasattr(d, "to_pydatetime"):
            return d.to_pydatetime().date()
        return dt.date.fromisoformat(str(d)[:10])

    for d, cur in zip(inflation_rate.index, inflation_rate):
        if pd.isna(cur):
            out.append(None)
            continue
        n = bisect_right(release_days, _as_date(d))
        if n < min_releases:
            out.append(None)
            continue
        h = release_vals[:n]
        cur_f = float(cur)
        p = sum(1 for x in h if x <= cur_f) / n
        if p <= 1.0 / 3.0:
            out.append("low")
        elif p <= 2.0 / 3.0:
            out.append("normal")
        else:
            out.append("high")
    return out


def assemble_macro_frame(
    trading_days: list[dt.date],
    series: dict[str, pd.Series],
    *,
    inflation_releases: list[tuple[dt.date, float]],
) -> pd.DataFrame:
    """Assemble full macro_conditions frame for all trading days."""
    frame = pd.DataFrame({"date": trading_days})
    for col in (
        "inflation_rate",
        "core_inflation_rate",
        "unemployment_rate",
        "jobless_claims",
        "fed_funds_rate",
        "treasury_2y_yield",
        "treasury_10y_yield",
        "fed_balance_sheet",
        "credit_spread",
    ):
        s = series[col]
        frame[col] = s.reindex(trading_days).to_numpy()

    frame["yield_curve_10y_2y"] = derive_yield_curve(frame)
    frame["inflation_regime"] = derive_inflation_regime(
        pd.Series(frame["inflation_rate"].to_numpy(), index=trading_days),
        inflation_releases,
    )
    frame["rate_regime"] = derive_rate_regime(frame["fed_funds_rate"])
    return frame


def load_trading_days(engine: Engine) -> list[dt.date]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT date FROM trading_days ORDER BY date")).all()
    if not rows:
        raise MacroConditionsValidationError("trading_days is empty")
    return [r[0] for r in rows]


def upsert_macro_conditions(
    engine: Engine,
    frame: pd.DataFrame,
    *,
    batch_size: int = 500,
) -> int:
    if frame.empty:
        return 0
    cols = ["date", *MACRO_COLUMNS]
    records = frame[cols].to_dict(orient="records")
    for rec in records:
        for col in MACRO_COLUMNS:
            rec[col] = _nan_to_none(rec[col])

    with engine.begin() as conn:
        # Replace full table content for true idempotent spine sync
        conn.execute(text("DELETE FROM macro_conditions"))
        for offset in range(0, len(records), batch_size):
            batch = records[offset : offset + batch_size]
            stmt = insert(MacroCondition).values(batch)
            conn.execute(stmt)
    return len(records)
