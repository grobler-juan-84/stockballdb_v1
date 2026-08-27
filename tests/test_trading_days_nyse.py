"""NYSE calendar spot checks for trading_days generation."""

from __future__ import annotations

import datetime as dt

from stockballdb.calendar.nyse import get_nyse_valid_dates
from stockballdb.calendar.trading_days_build import build_trading_days_frame
from stockballdb.calendar.validate import KNOWN_CLOSED, KNOWN_OPEN, validate_trading_days_frame


def test_nyse_excludes_known_closures() -> None:
    dates = set(
        get_nyse_valid_dates(start=dt.date(1985, 1, 1), end=dt.date(2013, 12, 31))
    )
    for closed in KNOWN_CLOSED:
        assert closed not in dates


def test_nyse_includes_known_sessions() -> None:
    dates = set(
        get_nyse_valid_dates(start=dt.date(1960, 1, 1), end=dt.date(2020, 12, 31))
    )
    for opened in KNOWN_OPEN:
        assert opened in dates


def test_build_frame_deterministic_and_valid() -> None:
    end = dt.date(2020, 12, 31)
    a = build_trading_days_frame(start=dt.date(1957, 1, 1), end=end)
    b = build_trading_days_frame(start=dt.date(1957, 1, 1), end=end)
    assert a.equals(b)
    assert a["date"].iloc[0] == dt.date(1957, 1, 2)
    assert a["date"].iloc[-1] == end or a["date"].iloc[-1] <= end
    # 2020-12-31 was a Thursday and an NYSE session
    assert dt.date(2020, 12, 31) in set(a["date"])
    validate_trading_days_frame(a)
    assert a["prev_trading_date"].iloc[0] is None
    assert a["next_trading_date"].iloc[-1] is None
