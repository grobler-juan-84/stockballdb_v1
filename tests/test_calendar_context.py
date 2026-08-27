"""Deterministic tests for calendar_context derivation."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from stockballdb.calendar_context.derive import (
    derive_calendar_context_frame,
    effective_session,
)
from stockballdb.calendar_context.holidays import (
    HolidayCatalog,
    early_close_dates,
    resolve_gap_closures,
    weekdays_between,
)
from stockballdb.calendar_context.validate import (
    assert_no_forward_dependency,
    validate_frame,
)


def _trading_frame(dates: list[dt.date]) -> pd.DataFrame:
    rows = []
    for i, d in enumerate(dates):
        prev = dates[i - 1] if i else None
        nxt = dates[i + 1] if i + 1 < len(dates) else None
        # minimal fields used by derive
        month_dates = [x for x in dates if x.year == d.year and x.month == d.month]
        td_m = month_dates.index(d) + 1
        is_me = d == month_dates[-1]
        q = (d.month - 1) // 3 + 1
        q_dates = [
            x
            for x in dates
            if x.year == d.year and (x.month - 1) // 3 + 1 == q
        ]
        y_dates = [x for x in dates if x.year == d.year]
        rows.append(
            {
                "date": d,
                "weekday": d.isoweekday(),
                "month": d.month,
                "quarter": q,
                "year": d.year,
                "trading_day_of_month": td_m,
                "trading_day_of_year": y_dates.index(d) + 1,
                "is_month_end": is_me,
                "is_quarter_end": d == q_dates[-1],
                "is_year_end": d == y_dates[-1],
                "prev_trading_date": prev,
                "next_trading_date": nxt,
            }
        )
    return pd.DataFrame(rows)


def test_weekend_not_holiday_adjacency() -> None:
    # Fri -> Mon: weekend only
    dates = [
        dt.date(2024, 3, 22),  # Fri
        dt.date(2024, 3, 25),  # Mon
    ]
    frame = derive_calendar_context_frame(
        _trading_frame(dates),
        {k: [] for k in ("fomc", "cpi", "employment_situation", "election")},
        early_closes=set(),
        catalog=HolidayCatalog(start=dates[0], end=dates[-1]),
    )
    fri = frame.loc[frame["date"] == dates[0]].iloc[0]
    mon = frame.loc[frame["date"] == dates[1]].iloc[0]
    assert fri["is_day_before_holiday"] is False
    assert mon["is_day_after_holiday"] is False
    assert fri["holiday_name"] is None


def test_good_friday_adjacency() -> None:
    # 2024-03-28 Thu -> 2024-04-01 Mon, Good Friday 2024-03-29
    dates = [
        dt.date(2024, 3, 27),
        dt.date(2024, 3, 28),
        dt.date(2024, 4, 1),
        dt.date(2024, 4, 2),
    ]
    catalog = HolidayCatalog(start=dates[0], end=dates[-1])
    frame = derive_calendar_context_frame(
        _trading_frame(dates),
        {k: [] for k in ("fomc", "cpi", "employment_situation", "election")},
        early_closes=set(),
        catalog=catalog,
    )
    thu = frame.loc[frame["date"] == dt.date(2024, 3, 28)].iloc[0]
    mon = frame.loc[frame["date"] == dt.date(2024, 4, 1)].iloc[0]
    assert thu["is_day_before_holiday"] is True
    assert mon["is_day_after_holiday"] is True
    assert thu["holiday_type"] == "regular"
    assert "Good Friday" in (thu["holiday_name"] or "")
    assert mon["holiday_type"] == "regular"


def test_exceptional_911_closure() -> None:
    dates = [
        dt.date(2001, 9, 10),
        dt.date(2001, 9, 17),
        dt.date(2001, 9, 18),
    ]
    catalog = HolidayCatalog(start=dates[0], end=dates[-1])
    frame = derive_calendar_context_frame(
        _trading_frame(dates),
        {k: [] for k in ("fomc", "cpi", "employment_situation", "election")},
        early_closes=set(),
        catalog=catalog,
    )
    d10 = frame.loc[frame["date"] == dt.date(2001, 9, 10)].iloc[0]
    d17 = frame.loc[frame["date"] == dt.date(2001, 9, 17)].iloc[0]
    assert d10["is_day_before_holiday"] is True
    assert d17["is_day_after_holiday"] is True
    assert d10["holiday_type"] == "exceptional"
    assert d17["holiday_type"] == "exceptional"
    assert d10["holiday_name"] is not None


def test_thanksgiving_early_close() -> None:
    dates = [
        dt.date(2023, 11, 22),
        dt.date(2023, 11, 24),  # early close
        dt.date(2023, 11, 27),
    ]
    ec = {dt.date(2023, 11, 24)}
    catalog = HolidayCatalog(start=dates[0], end=dates[-1])
    frame = derive_calendar_context_frame(
        _trading_frame(dates),
        {k: [] for k in ("fomc", "cpi", "employment_situation", "election")},
        early_closes=ec,
        catalog=catalog,
    )
    assert bool(
        frame.loc[frame["date"] == dt.date(2023, 11, 24), "is_shortened_trading_day"].iloc[0]
    )
    assert not bool(
        frame.loc[frame["date"] == dt.date(2023, 11, 22), "is_shortened_trading_day"].iloc[0]
    )
    # Thanksgiving itself is a full closure, not a shortened session
    assert dt.date(2023, 11, 23) not in ec


def test_iso_week_year_boundary_and_counts() -> None:
    # ISO week spanning years must not use calendar year grouping
    dates = [
        dt.date(2024, 12, 30),  # Mon ISO week 1 of 2025
        dt.date(2024, 12, 31),
        dt.date(2025, 1, 2),
        dt.date(2025, 1, 3),
    ]
    # All four are ISO year 2025 week 1
    assert all(d.isocalendar()[:2] == (2025, 1) for d in dates)
    frame = derive_calendar_context_frame(
        _trading_frame(dates),
        {k: [] for k in ("fomc", "cpi", "employment_situation", "election")},
        early_closes=set(),
        catalog=HolidayCatalog(start=dates[0], end=dates[-1]),
    )
    assert (frame["trading_days_in_week"] == 4).all()
    assert frame["is_shortened_week"].all()


def test_transitions_month_quarter_year() -> None:
    dates = [
        dt.date(2023, 12, 28),
        dt.date(2023, 12, 29),  # year/quarter/month end
        dt.date(2024, 1, 2),  # first of year/quarter/month
        dt.date(2024, 1, 3),
        dt.date(2024, 3, 28),  # quarter end
        dt.date(2024, 4, 1),  # first of Q2
    ]
    frame = derive_calendar_context_frame(
        _trading_frame(dates),
        {k: [] for k in ("fomc", "cpi", "employment_situation", "election")},
        early_closes=set(),
        catalog=HolidayCatalog(start=dates[0], end=dates[-1]),
    )
    by = frame.set_index("date")
    assert by.loc[dt.date(2023, 12, 29), "is_turn_of_month"]
    assert by.loc[dt.date(2023, 12, 29), "is_year_transition"]
    assert by.loc[dt.date(2023, 12, 29), "is_quarter_transition"]
    assert by.loc[dt.date(2024, 1, 2), "is_turn_of_month"]
    assert by.loc[dt.date(2024, 1, 2), "is_year_transition"]
    assert by.loc[dt.date(2024, 4, 1), "is_quarter_transition"]
    assert not by.loc[dt.date(2024, 1, 3), "is_year_transition"]


def test_event_flags_and_days_since_on_calendar() -> None:
    dates = [
        dt.date(2020, 4, 28),
        dt.date(2020, 4, 29),  # FOMC
        dt.date(2020, 4, 30),
        dt.date(2020, 5, 1),
    ]
    events = {
        "fomc": [dt.date(2020, 4, 29)],
        "cpi": [],
        "employment_situation": [],
        "election": [],
    }
    frame = derive_calendar_context_frame(
        _trading_frame(dates),
        events,
        early_closes=set(),
        catalog=HolidayCatalog(start=dates[0], end=dates[-1]),
    )
    by = frame.set_index("date")
    assert by.loc[dt.date(2020, 4, 28), "days_since_last_fomc"] is None or pd.isna(
        by.loc[dt.date(2020, 4, 28), "days_since_last_fomc"]
    )
    assert by.loc[dt.date(2020, 4, 29), "is_fomc_day"]
    assert by.loc[dt.date(2020, 4, 29), "days_since_last_fomc"] == 0
    assert not by.loc[dt.date(2020, 4, 30), "is_fomc_day"]
    assert by.loc[dt.date(2020, 4, 30), "days_since_last_fomc"] == 1
    assert by.loc[dt.date(2020, 5, 1), "days_since_last_fomc"] == 2


def test_off_calendar_election_effective_session() -> None:
    # 1980-11-04 election was NYSE holiday (Tue); next session 1980-11-05
    dates = [
        dt.date(1980, 11, 3),
        dt.date(1980, 11, 5),
        dt.date(1980, 11, 6),
    ]
    election = dt.date(1980, 11, 4)
    assert election not in set(dates)
    events = {
        "fomc": [],
        "cpi": [],
        "employment_situation": [],
        "election": [election],
    }
    frame = derive_calendar_context_frame(
        _trading_frame(dates),
        events,
        early_closes=set(),
        catalog=HolidayCatalog(start=dates[0], end=dates[-1]),
    )
    by = frame.set_index("date")
    assert not by["is_election_day"].any()
    assert by.loc[dt.date(1980, 11, 5), "days_since_last_election"] == 0
    assert by.loc[dt.date(1980, 11, 6), "days_since_last_election"] == 1
    assert pd.isna(by.loc[dt.date(1980, 11, 3), "days_since_last_election"])


def test_effective_session_helper() -> None:
    days = [dt.date(2020, 1, 2), dt.date(2020, 1, 3), dt.date(2020, 1, 6)]
    s = set(days)
    assert effective_session(dt.date(2020, 1, 3), s, days) == dt.date(2020, 1, 3)
    assert effective_session(dt.date(2020, 1, 4), s, days) == dt.date(2020, 1, 6)
    assert effective_session(dt.date(2020, 1, 7), s, days) is None


def test_weekdays_between_skips_weekend_only() -> None:
    fri = dt.date(2024, 3, 22)
    mon = dt.date(2024, 3, 25)
    assert weekdays_between(fri, mon) == []


def test_validate_frame_and_no_forward() -> None:
    dates = [dt.date(2024, 1, 2), dt.date(2024, 1, 3), dt.date(2024, 1, 4)]
    frame = derive_calendar_context_frame(
        _trading_frame(dates),
        {k: [] for k in ("fomc", "cpi", "employment_situation", "election")},
        early_closes=set(),
        catalog=HolidayCatalog(start=dates[0], end=dates[-1]),
    )
    validate_frame(frame, dates)
    assert_no_forward_dependency(frame)


def test_early_closes_api_includes_thanksgiving_2023() -> None:
    ec = early_close_dates(dt.date(2023, 11, 1), dt.date(2023, 11, 30))
    assert dt.date(2023, 11, 24) in ec


def test_cpi_employment_election_modern_flags() -> None:
    dates = [
        dt.date(2020, 3, 6),
        dt.date(2020, 3, 11),
        dt.date(2020, 11, 3),
    ]
    events = {
        "fomc": [],
        "cpi": [dt.date(2020, 3, 11)],
        "employment_situation": [dt.date(2020, 3, 6)],
        "election": [dt.date(2020, 11, 3)],
    }
    frame = derive_calendar_context_frame(
        _trading_frame(dates),
        events,
        early_closes=set(),
        catalog=HolidayCatalog(start=dates[0], end=dates[-1]),
    )
    by = frame.set_index("date")
    assert by.loc[dt.date(2020, 3, 6), "is_employment_situation_day"]
    assert by.loc[dt.date(2020, 3, 11), "is_cpi_release_day"]
    assert by.loc[dt.date(2020, 11, 3), "is_election_day"]
