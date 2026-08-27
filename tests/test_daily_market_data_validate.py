"""Validation-focused tests for daily_market_data."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from stockballdb.market_data.validate import (
    DailyMarketDataValidationError,
    validate_daily_market_data_frame,
)


def _row(**overrides):
    base = {
        "date": dt.date(2024, 1, 2),
        "symbol": "SPY",
        "open": 10.0,
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
    base.update(overrides)
    return base


def test_rejects_duplicate_keys() -> None:
    frame = pd.DataFrame([_row(), _row()])
    with pytest.raises(DailyMarketDataValidationError, match="duplicate"):
        validate_daily_market_data_frame(
            frame,
            trading_days={dt.date(2024, 1, 2)},
            required_symbols=("SPY",),
        )


def test_rejects_missing_required_symbol() -> None:
    frame = pd.DataFrame([_row()])
    with pytest.raises(DailyMarketDataValidationError, match="missing required"):
        validate_daily_market_data_frame(
            frame,
            trading_days={dt.date(2024, 1, 2)},
            required_symbols=("SPY", "QQQ"),
        )
