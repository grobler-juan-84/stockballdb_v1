"""Unit tests for asset_regimes derivation and point-in-time integrity."""

from __future__ import annotations

import datetime as dt
import math

import numpy as np
import pandas as pd
import pytest

from stockballdb.regimes.derive import (
    VOL_ANNUALIZATION,
    VOL_REGIME_MIN_OBS,
    derive_asset_regimes,
)
from stockballdb.regimes.validate import (
    assert_volatility_regime_is_point_in_time,
    validate_asset_regimes_frame,
    validate_volatility_formula_sample,
)


def _synthetic_etf(n: int, start: dt.date = dt.date(2020, 1, 2)) -> pd.DataFrame:
    rows = []
    d = start
    price = 100.0
    for i in range(n):
        while d.isoweekday() > 5:
            d += dt.timedelta(days=1)
        adj = price + i * 0.1 + (0.5 if i % 17 == 0 else 0.0)
        prev = price + (i - 1) * 0.1 + (0.5 if (i - 1) % 17 == 0 else 0.0) if i else None
        r1 = None if prev is None else adj / prev - 1.0
        rows.append(
            {
                "date": d,
                "symbol": "SPY",
                "adj_close": adj,
                "return_1d": r1,
                "drawdown_from_high": 0.0,
            }
        )
        d += dt.timedelta(days=1)
    frame = pd.DataFrame(rows)
    # Proper expanding drawdown
    high = frame["adj_close"].cummax()
    frame["drawdown_from_high"] = frame["adj_close"] / high - 1.0
    return frame


def test_null_boundaries_and_asset_type() -> None:
    frame = derive_asset_regimes(_synthetic_etf(400))
    validate_asset_regimes_frame(frame)
    assert (frame["asset_type"] == "etf").all()
    assert frame["return_5d"].isna().sum() == 5
    assert frame["return_20d"].isna().sum() == 20
    assert frame["return_60d"].isna().sum() == 60
    assert frame["above_20dma"].isna().sum() == 19
    assert frame["above_50dma"].isna().sum() == 49
    assert frame["above_200dma"].isna().sum() == 199
    assert frame["volatility_20d"].isna().sum() == 20
    assert frame["trend_regime"].isna().sum() == 199
    assert frame["momentum_regime"].isna().sum() == 60
    # 20 null vols + first 251 valid vols before regime => 271 null regimes
    assert frame["volatility_regime"].isna().sum() == 20 + (VOL_REGIME_MIN_OBS - 1)


def test_trailing_return_and_sma_formulas() -> None:
    src = _synthetic_etf(30)
    out = derive_asset_regimes(src)
    # return_5d at iloc 5
    assert out.iloc[5]["return_5d"] == pytest.approx(
        src.iloc[5]["adj_close"] / src.iloc[0]["adj_close"] - 1
    )
    sma20 = src["adj_close"].iloc[:20].mean()
    assert out.iloc[19]["distance_20dma_pct"] == pytest.approx(
        src.iloc[19]["adj_close"] / sma20 - 1
    )
    assert out.iloc[19]["above_20dma"] == (src.iloc[19]["adj_close"] > sma20)


def test_equality_above_dma_is_false() -> None:
    # Construct flat prices so close == SMA
    rows = []
    d = dt.date(2020, 1, 2)
    for i in range(25):
        while d.isoweekday() > 5:
            d += dt.timedelta(days=1)
        rows.append(
            {
                "date": d,
                "symbol": "SPY",
                "adj_close": 100.0,
                "return_1d": None if i == 0 else 0.0,
                "drawdown_from_high": 0.0,
            }
        )
        d += dt.timedelta(days=1)
    out = derive_asset_regimes(pd.DataFrame(rows))
    assert out.iloc[19]["above_20dma"] is False
    assert out.iloc[19]["distance_20dma_pct"] == pytest.approx(0.0)


def test_volatility_ddof1_annualized() -> None:
    src = _synthetic_etf(40)
    out = derive_asset_regimes(src)
    validate_volatility_formula_sample(out)
    r = src["return_1d"].astype(float)
    expected = r.rolling(20, min_periods=20).std(ddof=1) * math.sqrt(252)
    assert out.iloc[20]["volatility_20d"] == pytest.approx(float(expected.iloc[20]))
    alt = r.rolling(20, min_periods=20).std(ddof=0) * math.sqrt(252)
    assert out.iloc[20]["volatility_20d"] != pytest.approx(float(alt.iloc[20]))


def test_drawdown_identity() -> None:
    src = _synthetic_etf(50)
    out = derive_asset_regimes(src)
    assert np.allclose(
        out["drawdown_pct"].astype(float),
        src["drawdown_from_high"].astype(float),
        equal_nan=True,
    )


def test_trend_and_momentum_vocabulary() -> None:
    src = _synthetic_etf(250)
    out = derive_asset_regimes(src)
    assert set(out["trend_regime"].dropna().unique()) <= {
        "uptrend",
        "downtrend",
        "neutral",
    }
    assert set(out["momentum_regime"].dropna().unique()) <= {
        "positive",
        "negative",
        "mixed",
    }


def test_momentum_zero_is_mixed() -> None:
    # Build enough history with a zero 20d return window conceptually via flat then bump
    rows = []
    d = dt.date(2020, 1, 2)
    prices = [100.0] * 70
    prices[69] = 100.0  # flat => return_20d and return_60d ~ 0 at end
    for i, adj in enumerate(prices):
        while d.isoweekday() > 5:
            d += dt.timedelta(days=1)
        prev = prices[i - 1] if i else None
        rows.append(
            {
                "date": d,
                "symbol": "SPY",
                "adj_close": adj,
                "return_1d": None if prev is None else adj / prev - 1.0,
                "drawdown_from_high": 0.0,
            }
        )
        d += dt.timedelta(days=1)
    out = derive_asset_regimes(pd.DataFrame(rows))
    assert out.iloc[69]["return_20d"] == pytest.approx(0.0)
    assert out.iloc[69]["return_60d"] == pytest.approx(0.0)
    assert out.iloc[69]["momentum_regime"] == "mixed"


def test_qqq_split_trailing_return_uses_adj() -> None:
    df = pd.DataFrame(
        [
            {
                "date": dt.date(2000, 3, 13),
                "symbol": "QQQ",
                "adj_close": 93.9,
                "return_1d": 0.01,
                "drawdown_from_high": 0.0,
            },
            {
                "date": dt.date(2000, 3, 14),
                "symbol": "QQQ",
                "adj_close": 90.5,
                "return_1d": -0.036,
                "drawdown_from_high": -0.036,
            },
            {
                "date": dt.date(2000, 3, 15),
                "symbol": "QQQ",
                "adj_close": 86.8,
                "return_1d": -0.041,
                "drawdown_from_high": -0.075,
            },
            {
                "date": dt.date(2000, 3, 16),
                "symbol": "QQQ",
                "adj_close": 91.8,
                "return_1d": 0.057,
                "drawdown_from_high": -0.022,
            },
            {
                "date": dt.date(2000, 3, 17),
                "symbol": "QQQ",
                "adj_close": 93.5,
                "return_1d": 0.019,
                "drawdown_from_high": -0.004,
            },
            {
                "date": dt.date(2000, 3, 20),
                "symbol": "QQQ",
                "adj_close": 90.9,
                "return_1d": -0.028,
                "drawdown_from_high": -0.032,
            },
        ]
    )
    out = derive_asset_regimes(df)
    r5 = out.iloc[5]["return_5d"]
    assert r5 == pytest.approx(90.9 / 93.9 - 1)
    assert abs(r5) < 0.1


def test_volatility_regime_point_in_time_anti_leakage() -> None:
    # Long series with changing vol so expanding != full-sample
    rng = np.random.default_rng(0)
    n = 400
    rows = []
    d = dt.date(2010, 1, 4)
    price = 100.0
    for i in range(n):
        while d.isoweekday() > 5:
            d += dt.timedelta(days=1)
        # Early low vol, later high vol
        shock = rng.normal(0, 0.002 if i < 200 else 0.03)
        new_price = price * (1 + shock)
        rows.append(
            {
                "date": d,
                "symbol": "SPY",
                "adj_close": new_price,
                "return_1d": None if i == 0 else new_price / price - 1.0,
                "drawdown_from_high": 0.0,
            }
        )
        price = new_price
        d += dt.timedelta(days=1)
    src = pd.DataFrame(rows)
    high = src["adj_close"].cummax()
    src["drawdown_from_high"] = src["adj_close"] / high - 1.0
    out = derive_asset_regimes(src)
    assert_volatility_regime_is_point_in_time(out)

    # Inject a leaky full-sample labeling and ensure the assertion would fail
    leaky = out.copy()
    vol = leaky["volatility_20d"]
    valid = vol.dropna().to_numpy(dtype=float)
    hist_count = 0
    leak_labels = []
    for v in vol:
        if pd.isna(v):
            leak_labels.append(None)
            continue
        hist_count += 1
        if hist_count < VOL_REGIME_MIN_OBS:
            leak_labels.append(None)
            continue
        p = (valid <= float(v)).mean()
        if p <= 1 / 3:
            leak_labels.append("low")
        elif p <= 2 / 3:
            leak_labels.append("normal")
        else:
            leak_labels.append("high")
    leaky["volatility_regime"] = leak_labels
    with pytest.raises(Exception):
        assert_volatility_regime_is_point_in_time(leaky)
