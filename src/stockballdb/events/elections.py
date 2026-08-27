"""U.S. presidential and midterm general Election Day generator."""

from __future__ import annotations

import datetime as dt

from stockballdb.events.types import COVERAGE_START, SOURCE_ELECTION, CanonicalEvent


def federal_election_day(year: int) -> dt.date:
    """First Tuesday after the first Monday in November (2 U.S.C. §7)."""
    # First Monday on or after Nov 1
    nov1 = dt.date(year, 11, 1)
    # weekday: Mon=0 ... Sun=6
    days_to_monday = (0 - nov1.weekday()) % 7
    first_monday = nov1 + dt.timedelta(days=days_to_monday)
    return first_monday + dt.timedelta(days=1)


def election_kind(year: int) -> str:
    if year % 4 == 0:
        return "presidential"
    if year % 4 == 2:
        return "midterm"
    raise ValueError(f"{year} is not a U.S. federal general-election year")


def acquire_election_events(
    *,
    start: dt.date = COVERAGE_START,
    end: dt.date,
) -> list[CanonicalEvent]:
    """Even-year federal general Election Days in [start, end]."""
    out: list[CanonicalEvent] = []
    year = start.year if start.year % 2 == 0 else start.year + 1
    while year <= end.year:
        if year % 2 == 0:
            try:
                kind = election_kind(year)
            except ValueError:
                year += 2
                continue
            day = federal_election_day(year)
            if start <= day <= end:
                out.append(
                    CanonicalEvent(
                        event_type="election",
                        event_date=day,
                        symbol=None,
                        reference_period=kind,
                        release_session="unknown",
                        event_time_et=None,
                        source=SOURCE_ELECTION,
                    )
                )
        year += 2
    return out
