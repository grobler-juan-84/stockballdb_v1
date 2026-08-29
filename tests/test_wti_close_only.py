"""Tests for WTI close-only market context normalization and validation."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from stockballdb.market_data.derive import derive_daily_market_fields
from stockballdb.market_data.normalize import normalize_fred_close_only_observations
from stockballdb.market_data.universe import WTI_SYMBOL
from stockballdb.market_data.validate import (
    DailyMarketDataValidationError,
    validate_daily_market_data_frame,
    validate_derived_market_data_frame,
)
from stockballdb.outcomes.derive import derive_market_outcomes


def test_normalize_fred_close_only_keeps_negative_april_2020() -> None:
    trading_days = {dt.date(2020, 4, 20), dt.date(2020, 4, 21)}
    observations = [
        {"date": "2020-04-20", "value": "-37.63"},
        {"date": "2020-04-21", "value": "10.01"},
    ]
    frame = normalize_fred_close_only_observations(
        WTI_SYMBOL,
        observations,
        trading_days=trading_days,
    )
    assert len(frame) == 2
    assert frame.iloc[0]["close"] == pytest.approx(-37.63)
    assert frame.iloc[0]["open"] is None or pd.isna(frame.iloc[0]["open"])
    assert frame.iloc[0]["adj_close"] is None or pd.isna(frame.iloc[0]["adj_close"])


def test_normalize_drops_non_trading_day_observations() -> None:
    trading_days = {dt.date(2024, 1, 2)}
    observations = [
        {"date": "2024-01-01", "value": "70.0"},
        {"date": "2024-01-02", "value": "71.0"},
    ]
    frame = normalize_fred_close_only_observations(
        WTI_SYMBOL,
        observations,
        trading_days=trading_days,
    )
    assert len(frame) == 1
    assert frame.iloc[0]["date"] == dt.date(2024, 1, 2)
    outside = frame.attrs["fred_dates_outside_trading_days"]
    assert dt.date(2024, 1, 1) in outside


def test_close_only_derived_fields() -> None:
    frame = normalize_fred_close_only_observations(
        WTI_SYMBOL,
        [
            {"date": "2024-01-02", "value": "70.0"},
            {"date": "2024-01-03", "value": "71.4"},
        ],
        trading_days={dt.date(2024, 1, 2), dt.date(2024, 1, 3)},
    )
    derived = derive_daily_market_fields(frame)
    validate_derived_market_data_frame(derived)
    assert pd.isna(derived.iloc[0]["return_1d"])
    assert derived.iloc[1]["return_1d"] == pytest.approx(71.4 / 70.0 - 1)
    assert derived["gap_pct"].isna().all()
    assert derived["intraday_return"].isna().all()
    assert derived["range_pct"].isna().all()
    assert derived.iloc[0]["drawdown_from_high"] == pytest.approx(0.0)


def test_rejects_fake_ohlc_for_close_only() -> None:
    frame = pd.DataFrame(
        [
            {
                "date": dt.date(2024, 1, 2),
                "symbol": WTI_SYMBOL,
                "open": 70.0,
                "high": 70.0,
                "low": 70.0,
                "close": 70.0,
                "volume": None,
                "adj_open": None,
                "adj_high": None,
                "adj_low": None,
                "adj_close": None,
                "adj_volume": None,
                "dividend_cash": None,
                "split_factor": None,
            }
        ]
    )
    with pytest.raises(DailyMarketDataValidationError, match="open must be NULL"):
        validate_daily_market_data_frame(
            frame,
            trading_days={dt.date(2024, 1, 2)},
            required_symbols=(WTI_SYMBOL,),
        )


def test_rejects_etf_missing_ohlc() -> None:
    frame = pd.DataFrame(
        [
            {
                "date": dt.date(2024, 1, 2),
                "symbol": "SPY",
                "open": None,
                "high": 12.0,
                "low": 9.0,
                "close": 11.0,
                "volume": 1000,
                "adj_open": 10.0,
                "adj_high": 12.0,
                "adj_low": 9.0,
                "adj_close": 11.0,
                "adj_volume": 1000,
                "dividend_cash": 0.0,
                "split_factor": 1.0,
            }
        ]
    )
    with pytest.raises(DailyMarketDataValidationError, match="null values in open"):
        validate_daily_market_data_frame(
            frame,
            trading_days={dt.date(2024, 1, 2)},
            required_symbols=("SPY",),
        )


def test_close_only_outcomes_have_null_range_metrics() -> None:
    frame = normalize_fred_close_only_observations(
        WTI_SYMBOL,
        [
            {"date": "2024-01-02", "value": "70.0"},
            {"date": "2024-01-03", "value": "71.0"},
            {"date": "2024-01-04", "value": "69.0"},
        ],
        trading_days={
            dt.date(2024, 1, 2),
            dt.date(2024, 1, 3),
            dt.date(2024, 1, 4),
        },
    )
    src = frame.assign(adj_close=pd.NA, adj_high=pd.NA, adj_low=pd.NA)
    outcomes = derive_market_outcomes(src)
    assert outcomes["max_up_5d"].isna().all()
    assert outcomes["max_down_5d"].isna().all()
    assert outcomes.iloc[0]["return_1d"] == pytest.approx(71.0 / 70.0 - 1)
