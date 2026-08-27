"""NYSE trading-session date source via pandas_market_calendars."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

CALENDAR_ID = "NYSE"
CALENDAR_START = dt.date(1957, 1, 1)
NY_TZ = ZoneInfo("America/New_York")


def today_ny() -> dt.date:
    """Return today's calendar date in America/New_York."""
    return dt.datetime.now(NY_TZ).date()


def get_nyse_valid_dates(
    start: dt.date = CALENDAR_START,
    end: dt.date | None = None,
) -> list[dt.date]:
    """
    Return sorted NYSE full-session dates from ``start`` through ``end`` inclusive.

    ``end`` defaults to the last completed calendar day in America/New_York
    (no future sessions). Early-close days are included as valid trading days.
    """
    if end is None:
        end = today_ny()
    if end < start:
        return []

    nyse = mcal.get_calendar(CALENDAR_ID)
    index = nyse.valid_days(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
    )
    dates = sorted({ts.date() for ts in index})
    return [d for d in dates if start <= d <= end]
