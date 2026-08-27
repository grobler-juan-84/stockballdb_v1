"""BLS CPI and Employment Situation release occurrences via ALFRED first prints."""

from __future__ import annotations

import datetime as dt

import requests

from stockballdb.events.types import (
    BLS_RELEASE_TIME_ET,
    BLS_TIME_CONFIDENT_FROM,
    COVERAGE_START,
    SOURCE_CPI,
    SOURCE_EMPLOYMENT,
    CanonicalEvent,
    reference_month,
)
from stockballdb.macro.pit import first_print_events, parse_alfred_rows
from stockballdb.providers.fred import fetch_all_vintages


def _bls_timing(event_date: dt.date) -> tuple[str, dt.time | None]:
    if event_date >= BLS_TIME_CONFIDENT_FROM:
        return "pre_open", BLS_RELEASE_TIME_ET
    # Date known; exact clock time not confidently asserted for V1.
    return "pre_open", None


def first_print_release_events(
    series_id: str,
    event_type: str,
    source: str,
    api_key: str,
    *,
    start: dt.date = COVERAGE_START,
    end: dt.date,
    session: requests.Session | None = None,
) -> list[CanonicalEvent]:
    """
    One event per reference-month first ALFRED print.

    Uses min(realtime_start) per observation date so later revisions do not
    create additional release events.
    """
    rows = fetch_all_vintages(series_id, api_key, session=session)
    vintages = parse_alfred_rows(rows)
    events = first_print_events(vintages)

    out: list[CanonicalEvent] = []
    seen_ids: set[str] = set()
    for realtime_start, ref_date, _value in events:
        if realtime_start < start or realtime_start > end:
            continue
        # Monthly series only — skip non-month-start obs if any
        if ref_date.day != 1:
            continue
        session_name, etime = _bls_timing(realtime_start)
        ev = CanonicalEvent(
            event_type=event_type,
            event_date=realtime_start,
            symbol=None,
            reference_period=reference_month(ref_date),
            release_session=session_name,
            event_time_et=etime,
            source=source,
        )
        if ev.event_id in seen_ids:
            continue
        seen_ids.add(ev.event_id)
        out.append(ev)
    out.sort(key=lambda e: (e.event_date, e.reference_period or ""))
    return out


def acquire_cpi_events(
    api_key: str,
    *,
    start: dt.date = COVERAGE_START,
    end: dt.date,
    session: requests.Session | None = None,
) -> list[CanonicalEvent]:
    return first_print_release_events(
        "CPIAUCSL",
        "cpi",
        SOURCE_CPI,
        api_key,
        start=start,
        end=end,
        session=session,
    )


def acquire_employment_situation_events(
    api_key: str,
    *,
    start: dt.date = COVERAGE_START,
    end: dt.date,
    session: requests.Session | None = None,
) -> list[CanonicalEvent]:
    return first_print_release_events(
        "UNRATE",
        "employment_situation",
        SOURCE_EMPLOYMENT,
        api_key,
        start=start,
        end=end,
        session=session,
    )
