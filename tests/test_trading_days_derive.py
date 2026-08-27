"""Unit tests for trading_days derived columns."""

from __future__ import annotations

import datetime as dt

import pytest

from stockballdb.calendar.trading_days_build import derive_trading_days_frame
from stockballdb.calendar.validate import (
    TradingDaysValidationError,
    validate_trading_days_frame,
)


def test_derive_basic_columns_and_boundaries() -> None:
    dates = [
        dt.date(2024, 1, 2),
        dt.date(2024, 1, 3),
        dt.date(2024, 1, 4),
        dt.date(2024, 1, 5),
    ]
    frame = derive_trading_days_frame(dates)

    assert frame.iloc[0]["prev_trading_date"] is None
    assert frame.iloc[-1]["next_trading_date"] is None
    assert frame.iloc[0]["next_trading_date"] == dt.date(2024, 1, 3)
    assert frame.iloc[-1]["prev_trading_date"] == dt.date(2024, 1, 4)
    assert frame["trading_day_of_month"].tolist() == [1, 2, 3, 4]
    assert frame.iloc[-1]["days_to_month_end"] == 0
    assert bool(frame.iloc[-1]["is_month_end"]) is True
    assert frame.iloc[0]["weekday"] == 2  # Tuesday
    assert frame.iloc[0]["week_of_year"] == dt.date(2024, 1, 2).isocalendar().week


def test_iso_week_and_quarter_year_flags() -> None:
    # Sparse synthetic month spanning quarter end
    dates = [
        dt.date(2023, 12, 28),
        dt.date(2023, 12, 29),
        dt.date(2024, 1, 2),
    ]
    frame = derive_trading_days_frame(dates)
    assert bool(frame.iloc[1]["is_year_end"]) is True
    assert bool(frame.iloc[1]["is_quarter_end"]) is True
    assert bool(frame.iloc[0]["is_year_end"]) is False
    validate_trading_days_frame(frame)


def test_validation_rejects_weekend() -> None:
    dates = [dt.date(2024, 1, 2), dt.date(2024, 1, 6)]  # Saturday injected
    frame = derive_trading_days_frame(dates)
    # Force a weekend into the frame after derive
    frame.loc[1, "date"] = dt.date(2024, 1, 6)
    with pytest.raises(TradingDaysValidationError):
        validate_trading_days_frame(frame)
