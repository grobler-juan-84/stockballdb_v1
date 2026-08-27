"""Tests for Phase 2B derived daily_market_data fields."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from stockballdb.market_data.derive import derive_daily_market_fields
from stockballdb.market_data.validate import (
    DailyMarketDataValidationError,
    validate_derived_market_data_frame,
)


def _row(date, symbol, o, h, l, c, ao, ah, al, ac, **extra):
    base = {
        "date": date,
        "symbol": symbol,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": 1000,
        "adj_open": ao,
        "adj_high": ah,
        "adj_low": al,
        "adj_close": ac,
        "adj_volume": 1000,
        "dividend_cash": 0.0,
        "split_factor": 1.0,
    }
    base.update(extra)
    return base


def test_first_row_null_cross_day_fields() -> None:
    frame = pd.DataFrame(
        [
            _row(dt.date(2024, 1, 2), "SPY", 10, 11, 9, 10.5, 10, 11, 9, 10.5),
            _row(dt.date(2024, 1, 3), "SPY", 10.6, 11, 10, 10.8, 10.6, 11, 10, 10.8),
        ]
    )
    out = derive_daily_market_fields(frame)
    validate_derived_market_data_frame(out)
    assert pd.isna(out.iloc[0]["return_1d"])
    assert pd.isna(out.iloc[0]["gap_pct"])
    assert out.iloc[0]["drawdown_from_high"] == pytest.approx(0.0)
    assert out.iloc[1]["return_1d"] == pytest.approx(10.8 / 10.5 - 1)


def test_qqq_split_uses_adjusted_cross_day() -> None:
    """Synthetic numbers mirroring QQQ 2000-03-17 -> 2000-03-20 split behavior."""
    frame = pd.DataFrame(
        [
            _row(
                dt.date(2000, 3, 17),
                "QQQ",
                216,
                222.1,
                215.9,
                221.6,
                91.1184919112,
                93.691745618,
                91.0763074242,
                93.480823183,
            ),
            _row(
                dt.date(2000, 3, 20),
                "QQQ",
                111,
                111.5,
                106.3,
                107.7,
                93.649561131,
                94.0714060009,
                89.6842193534,
                90.8653849892,
                split_factor=2.0,
            ),
        ]
    )
    out = derive_daily_market_fields(frame)
    day = out.iloc[1]
    raw_ret = 107.7 / 221.6 - 1
    adj_ret = 90.8653849892 / 93.480823183 - 1
    assert day["return_1d"] == pytest.approx(adj_ret)
    assert abs(day["return_1d"] - raw_ret) > 0.4
    assert day["gap_pct"] == pytest.approx(93.649561131 / 93.480823183 - 1)
    assert day["intraday_return"] == pytest.approx(107.7 / 111 - 1)


def test_spy_dividend_adjusted_return_differs_from_raw() -> None:
    frame = pd.DataFrame(
        [
            _row(
                dt.date(2024, 3, 14),
                "SPY",
                516.97,
                517.125,
                511.82,
                514.95,
                501.8474516493,
                501.9979175468,
                496.848100863,
                499.8865412438,
            ),
            _row(
                dt.date(2024, 3, 15),
                "SPY",
                510.21,
                511.7,
                508.122,
                509.83,
                496.8346324962,
                498.2855715261,
                494.8013702852,
                496.4645943544,
                dividend_cash=1.594937,
            ),
        ]
    )
    out = derive_daily_market_fields(frame)
    day = out.iloc[1]
    raw_ret = 509.83 / 514.95 - 1
    adj_ret = 496.4645943544 / 499.8865412438 - 1
    assert day["return_1d"] == pytest.approx(adj_ret)
    assert day["return_1d"] != pytest.approx(raw_ret, abs=1e-6)
    assert day["intraday_return"] == pytest.approx(509.83 / 510.21 - 1)


def test_validate_rejects_non_null_first_return() -> None:
    frame = pd.DataFrame(
        [
            _row(dt.date(2024, 1, 2), "SPY", 10, 11, 9, 10, 10, 11, 9, 10),
            _row(dt.date(2024, 1, 3), "SPY", 10, 11, 9, 11, 10, 11, 9, 11),
        ]
    )
    out = derive_daily_market_fields(frame)
    out.loc[0, "return_1d"] = 0.01
    with pytest.raises(DailyMarketDataValidationError, match="first row"):
        validate_derived_market_data_frame(out)
