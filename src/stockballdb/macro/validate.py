"""Validation for macro_conditions."""

from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from stockballdb.macro.align import TradingDayIndex, map_availability_to_trading_day
from stockballdb.macro.derive import MACRO_COLUMNS, MacroConditionsValidationError
from stockballdb.macro.series import INFLATION_REGIME_MIN_RELEASES, RATE_REGIME_LOOKBACK


def validate_macro_frame(frame: pd.DataFrame, expected_days: int) -> None:
    errors: list[str] = []
    if len(frame) != expected_days:
        errors.append(f"row count {len(frame)} != trading_days {expected_days}")
    if frame["date"].duplicated().any():
        errors.append("duplicate dates")
    for col in MACRO_COLUMNS:
        if col not in frame.columns:
            errors.append(f"missing column {col}")
    # yield curve identity
    both = frame["treasury_10y_yield"].notna() & frame["treasury_2y_yield"].notna()
    if both.any():
        calc = frame.loc[both, "treasury_10y_yield"] - frame.loc[both, "treasury_2y_yield"]
        diff = (calc - frame.loc[both, "yield_curve_10y_2y"]).abs().max()
        if float(diff) > 1e-9:
            errors.append("yield_curve_10y_2y mismatch")
    either_null = frame["treasury_10y_yield"].isna() | frame["treasury_2y_yield"].isna()
    if frame.loc[either_null, "yield_curve_10y_2y"].notna().any():
        errors.append("yield curve non-null when a leg is null")
    # no forward-fill check for a known sparse treasury day is hard without source;
    # regime vocab
    for col, allowed in (
        ("inflation_regime", {"low", "normal", "high"}),
        ("rate_regime", {"easing", "stable", "tightening"}),
    ):
        vals = set(frame[col].dropna().unique())
        if not vals.issubset(allowed):
            errors.append(f"{col} unexpected values {vals - allowed}")
    if errors:
        raise MacroConditionsValidationError("; ".join(errors))


def validate_macro_db(engine: Engine, *, expected_count: int) -> None:
    errors: list[str] = []
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM macro_conditions")).scalar_one()
        if count != expected_count:
            errors.append(f"macro_conditions count {count} != {expected_count}")
        td = conn.execute(text("SELECT COUNT(*) FROM trading_days")).scalar_one()
        if count != td:
            errors.append(f"macro_conditions {count} != trading_days {td}")
        orphan = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM macro_conditions m
                WHERE NOT EXISTS (
                  SELECT 1 FROM trading_days t WHERE t.date = m.date
                )
                """
            )
        ).scalar_one()
        if orphan:
            errors.append(f"orphan macro dates: {orphan}")
        # PMI column must not exist
        has_pmi = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_name = 'macro_conditions' AND column_name = 'pmi'
                """
            )
        ).scalar_one()
        if has_pmi:
            errors.append("pmi column present but deferred from V1")
    if errors:
        raise MacroConditionsValidationError("; ".join(errors))


def assert_alignment_helpers() -> None:
    """Unit-level release alignment conventions."""
    days = [
        dt.date(2024, 1, 2),
        dt.date(2024, 1, 3),
        dt.date(2024, 1, 4),
        dt.date(2024, 1, 5),
        dt.date(2024, 1, 8),
    ]
    td = TradingDayIndex(days)
    # pre-open on trading day
    assert map_availability_to_trading_day(dt.date(2024, 1, 3), "pre_open", td) == dt.date(
        2024, 1, 3
    )
    # pre-open on weekend -> next TD
    assert map_availability_to_trading_day(dt.date(2024, 1, 6), "pre_open", td) == dt.date(
        2024, 1, 8
    )
    # after-close on Thu 2024-01-04 -> Fri 2024-01-05
    assert map_availability_to_trading_day(
        dt.date(2024, 1, 4), "after_close", td
    ) == dt.date(2024, 1, 5)
    # observation_date miss
    assert map_availability_to_trading_day(dt.date(2024, 1, 6), "observation_date", td) is None


def assert_inflation_regime_uses_distinct_releases(
    inflation_releases: list[tuple[dt.date, float]],
    frame: pd.DataFrame,
) -> None:
    """Fail if regime could be assigned with fewer than 36 distinct releases."""
    if not inflation_releases:
        raise MacroConditionsValidationError("no inflation releases for regime check")
    # First non-null regime must occur only after 36 releases available
    first_reg = frame.loc[frame["inflation_regime"].notna()].head(1)
    if first_reg.empty:
        return
    d = first_reg.iloc[0]["date"]
    n = sum(1 for rd, _ in inflation_releases if rd <= d)
    if n < INFLATION_REGIME_MIN_RELEASES:
        raise MacroConditionsValidationError(
            f"inflation_regime set with only {n} distinct releases"
        )
    # Distinct count should be far smaller than non-null inflation trading days
    non_null_inf = int(frame["inflation_rate"].notna().sum())
    if len(inflation_releases) >= non_null_inf:
        raise MacroConditionsValidationError(
            "inflation releases not distinct relative to daily forward-filled rows"
        )


def assert_no_future_inflation_release_leak(
    inflation_releases: list[tuple[dt.date, float]],
    frame: pd.DataFrame,
) -> None:
    """Regime on day t must not depend on releases with availability > t."""
    from stockballdb.macro.derive import derive_inflation_regime

    # Truncate releases after a midpoint and ensure early rows unchanged
    if len(inflation_releases) < INFLATION_REGIME_MIN_RELEASES + 5:
        return
    mid = inflation_releases[len(inflation_releases) // 2][0]
    early = [(d, v) for d, v in inflation_releases if d <= mid]
    full = derive_inflation_regime(
        pd.Series(frame["inflation_rate"].to_numpy(), index=frame["date"]),
        inflation_releases,
    )
    trunc = derive_inflation_regime(
        pd.Series(frame["inflation_rate"].to_numpy(), index=frame["date"]),
        early,
    )
    for d, a, b in zip(frame["date"], full, trunc):
        if d <= mid and a != b:
            raise MacroConditionsValidationError(
                f"future inflation release leaked into regime on {d}: {a!r} vs {b!r}"
            )


def assert_rate_regime_lookback(frame: pd.DataFrame) -> None:
    ff = frame["fed_funds_rate"]
    non_null_idx = [i for i, v in enumerate(ff) if pd.notna(v)]
    if len(non_null_idx) <= RATE_REGIME_LOOKBACK:
        return
    # First RATE_REGIME_LOOKBACK non-null rows must have NULL regime
    for i in non_null_idx[:RATE_REGIME_LOOKBACK]:
        if frame.iloc[i]["rate_regime"] is not None and not pd.isna(
            frame.iloc[i]["rate_regime"]
        ):
            raise MacroConditionsValidationError(
                "rate_regime set before 63 prior non-NULL fed_funds observations"
            )
