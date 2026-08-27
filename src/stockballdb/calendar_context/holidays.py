"""NYSE holiday / early-close metadata for calendar_context."""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

import pandas as pd
import pandas_market_calendars as mcal

from stockballdb.calendar.nyse import CALENDAR_ID, CALENDAR_START


@lru_cache(maxsize=1)
def _nyse():
    return mcal.get_calendar(CALENDAR_ID)


def early_close_dates(start: dt.date, end: dt.date) -> set[dt.date]:
    """Trading dates with scheduled early closes (pinned NYSE calendar)."""
    nyse = _nyse()
    sched = nyse.schedule(start_date=start.isoformat(), end_date=end.isoformat())
    if sched.empty:
        return set()
    ec = nyse.early_closes(sched)
    return {ts.date() for ts in ec.index}


def _adhoc_dates() -> set[dt.date]:
    nyse = _nyse()
    out: set[dt.date] = set()
    for raw in nyse.adhoc_holidays:
        ts = pd.Timestamp(raw)
        if ts.tzinfo is not None:
            ts = ts.tz_convert(None)
        out.add(ts.normalize().date())
    return out


def _regular_name_by_date(start: dt.date, end: dt.date) -> dict[dt.date, str]:
    """Map calendar dates to regular NYSE holiday rule names."""
    nyse = _nyse()
    names: dict[dt.date, str] = {}
    start_ts = dt.datetime.combine(start, dt.time())
    end_ts = dt.datetime.combine(end, dt.time())
    for rule in nyse.regular_holidays.rules:
        try:
            dates = rule.dates(start_ts, end_ts)
        except Exception:
            continue
        if dates is None:
            continue
        for d in dates:
            day = pd.Timestamp(d).normalize().date()
            # Prefer first rule that matches; later overlapping rules keep first
            names.setdefault(day, str(rule.name))
    return names


class HolidayCatalog:
    """Resolve weekday closure names/types between trading sessions."""

    def __init__(self, start: dt.date = CALENDAR_START, end: dt.date | None = None):
        if end is None:
            end = dt.date.today()
        # Pad for closures just outside spine edges
        pad_start = start - dt.timedelta(days=14)
        pad_end = end + dt.timedelta(days=14)
        self.adhoc = _adhoc_dates()
        self.regular_names = _regular_name_by_date(pad_start, pad_end)

    def classify_closed_weekday(self, d: dt.date) -> tuple[str, str]:
        """
        Return (name, type) for a Mon–Fri closed date.

        type is 'regular' or 'exceptional'.
        """
        if d in self.adhoc:
            name = self.regular_names.get(d, "Exceptional Closure")
            return name, "exceptional"
        if d in self.regular_names:
            return self.regular_names[d], "regular"
        return "Market Closure", "regular"


def weekdays_between(a: dt.date, b: dt.date) -> list[dt.date]:
    """Monday–Friday dates strictly between a and b."""
    out: list[dt.date] = []
    d = a + dt.timedelta(days=1)
    while d < b:
        if d.weekday() < 5:  # Mon=0 .. Fri=4
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def resolve_gap_closures(
    a: dt.date,
    b: dt.date,
    trading_set: set[dt.date],
    catalog: HolidayCatalog,
) -> tuple[list[str], str | None]:
    """
    Closed weekdays in (a, b).

    Returns (ordered unique names, holiday_type or None).
    """
    names: list[str] = []
    seen: set[str] = set()
    types: list[str] = []
    for d in weekdays_between(a, b):
        if d in trading_set:
            continue
        name, htype = catalog.classify_closed_weekday(d)
        types.append(htype)
        if name not in seen:
            seen.add(name)
            names.append(name)
    if not names:
        return [], None
    htype = "exceptional" if "exceptional" in types else "regular"
    return names, htype
