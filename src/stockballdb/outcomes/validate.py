"""Validation for market_outcomes."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from stockballdb.market_data.universe import PHASE_2A_ETF_SYMBOLS
from stockballdb.outcomes.derive import OUTCOME_COLUMNS, MarketOutcomesValidationError


def validate_market_outcomes_frame(frame: pd.DataFrame) -> None:
    """Structural checks on a derived outcomes DataFrame."""
    errors: list[str] = []
    if frame.empty:
        raise MarketOutcomesValidationError("market_outcomes frame is empty")
    missing = [c for c in ("date", "symbol", *OUTCOME_COLUMNS) if c not in frame.columns]
    if missing:
        errors.append(f"missing columns: {missing}")
    if frame.duplicated(subset=["date", "symbol"]).any():
        errors.append("duplicate (date, symbol)")

    for symbol, group in frame.groupby("symbol"):
        g = group.sort_values("date").reset_index(drop=True)
        n = len(g)
        for horizon, col in (
            (1, "return_1d"),
            (3, "return_3d"),
            (5, "return_5d"),
            (10, "return_10d"),
            (20, "return_20d"),
        ):
            expected_nulls = min(horizon, n)
            actual_nulls = int(g[col].isna().sum())
            if actual_nulls != expected_nulls:
                errors.append(
                    f"{symbol}: {col} nulls={actual_nulls} expected={expected_nulls}"
                )
        for horizon, up_col, down_col in (
            (5, "max_up_5d", "max_down_5d"),
            (20, "max_up_20d", "max_down_20d"),
        ):
            expected_nulls = min(horizon, n)
            if int(g[up_col].isna().sum()) != expected_nulls:
                errors.append(f"{symbol}: {up_col} null count mismatch")
            if int(g[down_col].isna().sum()) != expected_nulls:
                errors.append(f"{symbol}: {down_col} null count mismatch")

        for ret_col, pos_col in (
            ("return_1d", "positive_1d"),
            ("return_5d", "positive_5d"),
            ("return_20d", "positive_20d"),
        ):
            for _, row in g.iterrows():
                ret = row[ret_col]
                pos = row[pos_col]
                if pd.isna(ret):
                    if not pd.isna(pos) and pos is not None:
                        errors.append(f"{symbol}: {pos_col} must be NULL when return NULL")
                        break
                else:
                    expected = bool(ret > 0)
                    if pos is None or pd.isna(pos) or bool(pos) != expected:
                        errors.append(f"{symbol}: {pos_col} mismatch vs {ret_col}")
                        break

    if errors:
        raise MarketOutcomesValidationError("; ".join(errors[:20]))


def validate_market_outcomes_db(
    engine: Engine,
    *,
    expected_count: int,
    required_symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
) -> None:
    """Validate persisted market_outcomes against daily_market_data."""
    errors: list[str] = []
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM market_outcomes")).scalar_one()
        if count != expected_count:
            errors.append(f"row count {count} != expected {expected_count}")

        dmd = conn.execute(text("SELECT COUNT(*) FROM daily_market_data")).scalar_one()
        if count != dmd:
            errors.append(
                f"market_outcomes rows {count} != daily_market_data rows {dmd}"
            )

        orphan = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM market_outcomes m
                WHERE NOT EXISTS (
                  SELECT 1 FROM daily_market_data d
                  WHERE d.date = m.date AND d.symbol = m.symbol
                )
                """
            )
        ).scalar_one()
        if orphan:
            errors.append(f"orphan outcomes without daily_market_data: {orphan}")

        for symbol in required_symbols:
            n = conn.execute(
                text("SELECT COUNT(*) FROM market_outcomes WHERE symbol = :s"),
                {"s": symbol},
            ).scalar_one()
            if n < 1:
                errors.append(f"no outcomes for {symbol}")

        # Consistency: outcomes.return_1d(t) ≈ dmd.return_1d(t+1)
        bad = conn.execute(
            text(
                """
                WITH ordered AS (
                  SELECT date, symbol, return_1d,
                    LEAD(date) OVER (PARTITION BY symbol ORDER BY date) AS next_date
                  FROM market_outcomes
                )
                SELECT COUNT(*) FROM ordered o
                JOIN daily_market_data d
                  ON d.symbol = o.symbol AND d.date = o.next_date
                WHERE o.return_1d IS NOT NULL
                  AND d.return_1d IS NOT NULL
                  AND ABS(o.return_1d - d.return_1d) > 1e-9
                """
            )
        ).scalar_one()
        if bad:
            errors.append(
                f"return_1d consistency failures vs next dmd.return_1d: {bad}"
            )

    if errors:
        raise MarketOutcomesValidationError("; ".join(errors))
