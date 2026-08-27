"""Unit tests for market_outcomes derivation."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from stockballdb.outcomes.derive import derive_market_outcomes
from stockballdb.outcomes.validate import validate_market_outcomes_frame


def _bars(n: int, start: dt.date = dt.date(2020, 1, 2)) -> pd.DataFrame:
    rows = []
    d = start
    price = 100.0
    for i in range(n):
        while d.isoweekday() > 5:
            d += dt.timedelta(days=1)
        rows.append(
            {
                "date": d,
                "symbol": "SPY",
                "adj_close": price + i,
                "adj_high": price + i + 1,
                "adj_low": price + i - 1,
            }
        )
        d += dt.timedelta(days=1)
    return pd.DataFrame(rows)


def test_horizon_null_counts() -> None:
    frame = derive_market_outcomes(_bars(25))
    validate_market_outcomes_frame(frame)
    assert frame["return_1d"].isna().sum() == 1
    assert frame["return_5d"].isna().sum() == 5
    assert frame["return_20d"].isna().sum() == 20
    assert frame["max_up_5d"].isna().sum() == 5
    assert frame["max_up_20d"].isna().sum() == 20


def test_return_and_max_formulas() -> None:
    frame = derive_market_outcomes(_bars(10))
    # index 0: adj_close=100, t+1 close=101, t+5 close=105
    assert frame.iloc[0]["return_1d"] == pytest.approx(101 / 100 - 1)
    assert frame.iloc[0]["return_5d"] == pytest.approx(105 / 100 - 1)
    # highs for t+1..t+5 are 102,103,104,105,106 → max 106
    assert frame.iloc[0]["max_up_5d"] == pytest.approx(106 / 100 - 1)
    # lows 100,101,102,103,104 → min 100
    assert frame.iloc[0]["max_down_5d"] == pytest.approx(100 / 100 - 1)
    assert frame.iloc[0]["positive_1d"] is True
    assert frame.iloc[0]["positive_5d"] is True


def test_positive_false_on_zero_and_negative() -> None:
    df = pd.DataFrame(
        [
            {
                "date": dt.date(2020, 1, 2),
                "symbol": "X",
                "adj_close": 100.0,
                "adj_high": 100.0,
                "adj_low": 100.0,
            },
            {
                "date": dt.date(2020, 1, 3),
                "symbol": "X",
                "adj_close": 100.0,
                "adj_high": 100.0,
                "adj_low": 99.0,
            },
            {
                "date": dt.date(2020, 1, 6),
                "symbol": "X",
                "adj_close": 90.0,
                "adj_high": 95.0,
                "adj_low": 90.0,
            },
        ]
    )
    out = derive_market_outcomes(df)
    assert out.iloc[0]["return_1d"] == pytest.approx(0.0)
    assert out.iloc[0]["positive_1d"] is False
    assert out.iloc[1]["return_1d"] == pytest.approx(90 / 100 - 1)
    assert out.iloc[1]["positive_1d"] is False
    assert out.iloc[2]["return_1d"] is None or pd.isna(out.iloc[2]["return_1d"])
    assert out.iloc[2]["positive_1d"] is None


def test_qqq_split_window_continuous() -> None:
    """Adjusted path through split day stays continuous (not ~-50%)."""
    df = pd.DataFrame(
        [
            {
                "date": dt.date(2000, 3, 17),
                "symbol": "QQQ",
                "adj_close": 93.480823183,
                "adj_high": 93.691745618,
                "adj_low": 91.0763074242,
            },
            {
                "date": dt.date(2000, 3, 20),
                "symbol": "QQQ",
                "adj_close": 90.8653849892,
                "adj_high": 94.0714060009,
                "adj_low": 89.6842193534,
            },
            {
                "date": dt.date(2000, 3, 21),
                "symbol": "QQQ",
                "adj_close": 94.3245129229,
                "adj_high": 94.4088818969,
                "adj_low": 87.4062570556,
            },
        ]
    )
    out = derive_market_outcomes(df)
    r1 = out.iloc[0]["return_1d"]
    assert r1 == pytest.approx(90.8653849892 / 93.480823183 - 1)
    assert abs(r1) < 0.1
