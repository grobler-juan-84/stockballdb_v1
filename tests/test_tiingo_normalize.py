"""Unit tests for Tiingo → canonical normalization."""

from __future__ import annotations

import datetime as dt

import pytest

from stockballdb.market_data.normalize import normalize_tiingo_bars
from stockballdb.market_data.validate import (
    DailyMarketDataValidationError,
    validate_daily_market_data_frame,
)

SAMPLE_BARS = [
    {
        "date": "2024-01-02T00:00:00.000Z",
        "close": 472.65,
        "high": 473.67,
        "low": 470.49,
        "open": 472.16,
        "volume": 123007793,
        "adjClose": 458.82,
        "adjHigh": 459.81,
        "adjLow": 456.72,
        "adjOpen": 458.34,
        "adjVolume": 123007793,
        "divCash": 0.0,
        "splitFactor": 1.0,
    },
    {
        "date": "2024-01-03T00:00:00.000Z",
        "close": 470.0,
        "high": 473.0,
        "low": 469.0,
        "open": 472.0,
        "volume": 100,
        "adjClose": 456.0,
        "adjHigh": 459.0,
        "adjLow": 455.0,
        "adjOpen": 458.0,
        "adjVolume": 100,
        "divCash": 1.5,
        "splitFactor": 1.0,
    },
]


def test_normalize_maps_tiingo_fields() -> None:
    trading_days = {dt.date(2024, 1, 2), dt.date(2024, 1, 3)}
    frame = normalize_tiingo_bars("spy", SAMPLE_BARS, trading_days=trading_days)

    assert list(frame["symbol"].unique()) == ["SPY"]
    assert frame.iloc[0]["adj_open"] == pytest.approx(458.34)
    assert frame.iloc[1]["dividend_cash"] == pytest.approx(1.5)
    assert frame.iloc[0]["split_factor"] == pytest.approx(1.0)
    assert "return_1d" not in frame.columns
    validate_daily_market_data_frame(
        frame,
        trading_days=trading_days,
        required_symbols=("SPY",),
    )


def test_normalize_excludes_dates_outside_trading_days() -> None:
    trading_days = {dt.date(2024, 1, 2)}
    frame = normalize_tiingo_bars("SPY", SAMPLE_BARS, trading_days=trading_days)
    assert len(frame) == 1
    assert frame.iloc[0]["date"] == dt.date(2024, 1, 2)
    outside = frame.attrs["tiingo_dates_outside_trading_days"]
    assert dt.date(2024, 1, 3) in outside


def test_validation_rejects_bad_ohlc() -> None:
    trading_days = {dt.date(2024, 1, 2)}
    bad = [
        {
            **SAMPLE_BARS[0],
            "high": 100.0,
            "low": 200.0,
        }
    ]
    frame = normalize_tiingo_bars("SPY", bad, trading_days=trading_days)
    with pytest.raises(DailyMarketDataValidationError, match="OHLC"):
        validate_daily_market_data_frame(
            frame,
            trading_days=trading_days,
            required_symbols=("SPY",),
        )
