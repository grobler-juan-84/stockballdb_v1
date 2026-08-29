"""Validation for asset_regimes."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from stockballdb.market_data.universe import (
    PHASE_2A_ETF_SYMBOLS,
    asset_type_for_symbol,
)
from stockballdb.regimes.derive import (
    REGIME_COLUMNS,
    VOL_ANNUALIZATION,
    VOL_REGIME_MIN_OBS,
    VOL_WINDOW,
    AssetRegimesValidationError,
    _expanding_volatility_regime,
)


def validate_asset_regimes_frame(frame: pd.DataFrame) -> None:
    """Structural checks on a derived asset_regimes DataFrame."""
    errors: list[str] = []
    if frame.empty:
        raise AssetRegimesValidationError("asset_regimes frame is empty")
    missing = [c for c in ("date", "symbol", *REGIME_COLUMNS) if c not in frame.columns]
    if missing:
        errors.append(f"missing columns: {missing}")
    if frame.duplicated(subset=["date", "symbol"]).any():
        errors.append("duplicate (date, symbol)")

    for symbol, group in frame.groupby("symbol"):
        g = group.sort_values("date").reset_index(drop=True)
        n = len(g)
        expected_type = asset_type_for_symbol(str(symbol))
        if (g["asset_type"] != expected_type).any():
            errors.append(
                f"{symbol}: asset_type must be {expected_type!r} for universe symbol"
            )

        checks = (
            ("return_5d", 5),
            ("return_20d", 20),
            ("return_60d", 60),
            ("above_20dma", 19),
            ("above_50dma", 49),
            ("above_200dma", 199),
            ("distance_20dma_pct", 19),
            ("distance_50dma_pct", 49),
            ("distance_200dma_pct", 199),
            ("volatility_20d", 20),
        )
        for col, expected_nulls in checks:
            expected = min(expected_nulls, n)
            actual = int(g[col].isna().sum())
            if actual != expected:
                errors.append(f"{symbol}: {col} nulls={actual} expected={expected}")

        # volatility_regime: NULL until 252 valid volatility_20d values
        vol_valid_count = g["volatility_20d"].notna().cumsum()
        for i, row in g.iterrows():
            vr = row["volatility_regime"]
            if vol_valid_count.iloc[i] < VOL_REGIME_MIN_OBS:
                if not (vr is None or pd.isna(vr)):
                    errors.append(f"{symbol}: volatility_regime set before 252 vol obs")
                    break
            else:
                if vr not in ("low", "normal", "high"):
                    errors.append(f"{symbol}: invalid volatility_regime={vr!r}")
                    break

        for i, row in g.iterrows():
            tr = row["trend_regime"]
            if pd.isna(row["above_200dma"]) or pd.isna(row["above_50dma"]):
                # SMA50/200 null => trend null (above_50dma nulls first 49; above_200 first 199)
                pass
            if pd.isna(row["distance_200dma_pct"]) or pd.isna(row["distance_50dma_pct"]):
                if not (tr is None or pd.isna(tr)):
                    errors.append(f"{symbol}: trend_regime set with incomplete SMAs")
                    break
            elif tr not in ("uptrend", "downtrend", "neutral"):
                errors.append(f"{symbol}: invalid trend_regime={tr!r}")
                break

        for i, row in g.iterrows():
            mr = row["momentum_regime"]
            if pd.isna(row["return_20d"]) or pd.isna(row["return_60d"]):
                if not (mr is None or pd.isna(mr)):
                    errors.append(f"{symbol}: momentum_regime set with incomplete returns")
                    break
            elif mr not in ("positive", "negative", "mixed"):
                errors.append(f"{symbol}: invalid momentum_regime={mr!r}")
                break

        # drawdown identity vs source column when present
        if "drawdown_from_high" in g.columns:
            mask = g["drawdown_from_high"].notna() & g["drawdown_pct"].notna()
            if mask.any():
                diff = (g.loc[mask, "drawdown_pct"] - g.loc[mask, "drawdown_from_high"]).abs()
                if float(diff.max()) > 1e-12:
                    errors.append(f"{symbol}: drawdown_pct != drawdown_from_high")

    if errors:
        raise AssetRegimesValidationError("; ".join(errors[:25]))


def validate_asset_regimes_db(
    engine: Engine,
    *,
    expected_count: int,
    required_symbols: tuple[str, ...] = PHASE_2A_ETF_SYMBOLS,
    symbol_scope: str | None = None,
) -> None:
    """Validate persisted asset_regimes against daily_market_data."""
    errors: list[str] = []
    with engine.connect() as conn:
        if symbol_scope:
            count = conn.execute(
                text("SELECT COUNT(*) FROM asset_regimes WHERE symbol = :symbol"),
                {"symbol": symbol_scope},
            ).scalar_one()
            dmd = conn.execute(
                text("SELECT COUNT(*) FROM daily_market_data WHERE symbol = :symbol"),
                {"symbol": symbol_scope},
            ).scalar_one()
        else:
            count = conn.execute(text("SELECT COUNT(*) FROM asset_regimes")).scalar_one()
            dmd = conn.execute(text("SELECT COUNT(*) FROM daily_market_data")).scalar_one()
        if count != expected_count:
            errors.append(f"row count {count} != expected {expected_count}")
        if count != dmd:
            errors.append(f"asset_regimes rows {count} != daily_market_data rows {dmd}")

        orphan = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM asset_regimes a
                WHERE NOT EXISTS (
                  SELECT 1 FROM daily_market_data d
                  WHERE d.date = a.date AND d.symbol = a.symbol
                )
                """
            )
        ).scalar_one()
        if orphan:
            errors.append(f"orphan regimes without daily_market_data: {orphan}")

        for symbol in required_symbols:
            n = conn.execute(
                text("SELECT COUNT(*) FROM asset_regimes WHERE symbol = :s"),
                {"s": symbol},
            ).scalar_one()
            if n < 1:
                errors.append(f"no regimes for {symbol}")

        dd_bad = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM asset_regimes a
                JOIN daily_market_data d ON d.date = a.date AND d.symbol = a.symbol
                WHERE a.drawdown_pct IS DISTINCT FROM d.drawdown_from_high
                """
            )
        ).scalar_one()
        if dd_bad:
            errors.append(f"drawdown identity failures: {dd_bad}")

        bad_types = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM asset_regimes a
                WHERE a.asset_type <> (
                  CASE a.symbol
                    WHEN 'WTI' THEN 'commodity'
                    ELSE 'etf'
                  END
                )
                """
            )
        ).scalar_one()
        if bad_types:
            errors.append(f"asset_type mismatches vs universe mapping: {bad_types}")

    if errors:
        raise AssetRegimesValidationError("; ".join(errors))


def assert_volatility_regime_is_point_in_time(frame: pd.DataFrame) -> None:
    """
    Fail if volatility_regime ranks used future or full-sample information.

    Recomputes expanding ranks through each date and compares labels.
    """
    required = {"date", "symbol", "volatility_20d", "volatility_regime"}
    missing = required - set(frame.columns)
    if missing:
        raise AssetRegimesValidationError(f"PIT check missing columns: {sorted(missing)}")

    for symbol, group in frame.groupby("symbol"):
        g = group.sort_values("date").reset_index(drop=True)
        # Full-sample ranks (FORBIDDEN) — build labels that would result from leakage
        vol = g["volatility_20d"]
        valid = vol.dropna()
        if len(valid) < VOL_REGIME_MIN_OBS:
            continue

        # Expanding recomputation must match stored labels
        expected = _expanding_volatility_regime(vol)
        for i, (got, exp) in enumerate(zip(g["volatility_regime"], expected)):
            got_n = None if got is None or (isinstance(got, float) and pd.isna(got)) else got
            if got_n != exp:
                raise AssetRegimesValidationError(
                    f"{symbol} row {i}: volatility_regime PIT mismatch "
                    f"stored={got_n!r} expected={exp!r}"
                )

        # Explicit anti-leakage: full-sample percentile labels must differ somewhere
        # from expanding labels for a long series (otherwise test is weak).
        full_vals = valid.to_numpy(dtype=float)
        full_labels: list[str | None] = []
        hist_count = 0
        for v in vol:
            if pd.isna(v):
                full_labels.append(None)
                continue
            hist_count += 1
            if hist_count < VOL_REGIME_MIN_OBS:
                full_labels.append(None)
                continue
            # LEAKY: percentile vs entire series including future
            p = (full_vals <= float(v)).mean()
            if p <= 1.0 / 3.0:
                full_labels.append("low")
            elif p <= 2.0 / 3.0:
                full_labels.append("normal")
            else:
                full_labels.append("high")

        diffs = sum(
            1
            for a, b in zip(expected, full_labels)
            if a is not None and b is not None and a != b
        )
        if diffs == 0 and hist_count >= VOL_REGIME_MIN_OBS + 50:
            raise AssetRegimesValidationError(
                f"{symbol}: expanding and full-sample vol regimes identical — "
                "anti-leakage test inconclusive or implementation may be leaky"
            )


def validate_volatility_formula_sample(frame: pd.DataFrame) -> None:
    """Spot-check volatility_20d uses ddof=1 and sqrt(252)."""
    for symbol, group in frame.groupby("symbol"):
        g = group.sort_values("date").reset_index(drop=True)
        if "return_1d" not in g.columns:
            continue
        r1 = pd.to_numeric(g["return_1d"], errors="coerce")
        expected = r1.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=1) * VOL_ANNUALIZATION
        mask = expected.notna() & g["volatility_20d"].notna()
        if not mask.any():
            continue
        diff = (expected[mask] - pd.to_numeric(g.loc[mask, "volatility_20d"])).abs().max()
        if float(diff) > 1e-10:
            raise AssetRegimesValidationError(
                f"{symbol}: volatility_20d formula mismatch max_diff={diff}"
            )
        # Ensure ddof=0 would differ on a sample row
        alt = r1.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=0) * VOL_ANNUALIZATION
        if mask.any() and float((expected[mask] - alt[mask]).abs().max()) < 1e-15:
            raise AssetRegimesValidationError(
                f"{symbol}: ddof=0 and ddof=1 unexpectedly identical"
            )
        break  # one symbol is enough for formula spot-check
