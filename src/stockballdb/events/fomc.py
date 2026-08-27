"""Parse and acquire regularly scheduled FOMC meeting decision days."""

from __future__ import annotations

import datetime as dt
import re
from html import unescape

import requests

from stockballdb.events.types import (
    COVERAGE_START,
    FOMC_STATEMENT_TIME_CONFIDENT_FROM,
    FOMC_STATEMENT_TIME_ET,
    SOURCE_FOMC,
    CanonicalEvent,
)
from stockballdb.providers.fed import fetch_text

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

EXCLUDE_RE = re.compile(
    r"unscheduled|conference\s+call|notation\s+vote|cancell?ed",
    re.IGNORECASE,
)

# e.g. "January 29-30 Meeting - 2019", "April/May 30-1 Meeting - 2019"
HIST_HEADING_RE = re.compile(
    r"^(?P<months>[A-Za-z]+(?:/[A-Za-z]+)?)\s+"
    r"(?P<d1>\d{1,2})(?:-(?P<d2>\d{1,2}))?\s+"
    r"(?P<label>.+?)\s*-\s*(?P<year>\d{4})\s*$",
    re.IGNORECASE,
)

H_TAG_RE = re.compile(r"<h[45][^>]*>(.*?)</h[45]>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")

CAL_PANEL_RE = re.compile(
    r"(?P<year>20\d{2})\s+FOMC\s+Meetings</a></h4>|"
    r"<h4[^>]*>\s*(?P<year2>20\d{2})\s+FOMC\s+Meetings",
    re.IGNORECASE,
)

CAL_MEETING_RE = re.compile(
    r'class="[^"]*fomc-meeting__month[^"]*"[^>]*>\s*<strong>\s*'
    r"(?P<month>[A-Za-z]+)\s*</strong>.*?"
    r'class="[^"]*fomc-meeting__date[^"]*"[^>]*>\s*'
    r"(?P<dates>\d{1,2}(?:\s*-\s*\d{1,2})?)\s*<",
    re.IGNORECASE | re.DOTALL,
)


def _strip_html(fragment: str) -> str:
    text = TAG_RE.sub("", fragment)
    return unescape(re.sub(r"\s+", " ", text)).strip()


def _parse_final_day(
    months_raw: str, d1: int, d2: int | None, year: int
) -> dt.date:
    parts = [p.strip().lower() for p in months_raw.split("/")]
    start_month = MONTHS[parts[0]]
    end_month = MONTHS[parts[1]] if len(parts) > 1 else start_month
    if d2 is None:
        return dt.date(year, start_month, d1)
    # Cross-month range: April/May 30-1 -> May 1
    if end_month != start_month:
        end_year = year if end_month >= start_month else year + 1
        return dt.date(end_year, end_month, d2)
    return dt.date(year, start_month, d2)


def parse_historical_heading(title: str) -> dt.date | None:
    """
    Return scheduled meeting final day, or None if excluded / not a meeting.
    """
    title = title.strip()
    if not title:
        return None
    if EXCLUDE_RE.search(title):
        return None
    if not re.search(r"\bMeeting\b", title, re.IGNORECASE):
        return None
    m = HIST_HEADING_RE.match(title)
    if not m:
        return None
    months = m.group("months")
    d1 = int(m.group("d1"))
    d2 = int(m.group("d2")) if m.group("d2") else None
    year = int(m.group("year"))
    try:
        return _parse_final_day(months, d1, d2, year)
    except (KeyError, ValueError):
        return None


def parse_historical_html(html: str) -> list[dt.date]:
    """Extract scheduled FOMC decision days from a year historical page."""
    out: list[dt.date] = []
    for frag in H_TAG_RE.findall(html):
        title = _strip_html(frag)
        day = parse_historical_heading(title)
        if day is not None:
            out.append(day)
    return out


def parse_calendars_html(html: str, *, years: set[int]) -> list[dt.date]:
    """Extract scheduled FOMC decision days from fomccalendars.htm panels."""
    # Split by year panel markers
    markers: list[tuple[int, int]] = []
    for m in re.finditer(
        r"(?P<year>20\d{2})\s+FOMC\s+Meetings", html, re.IGNORECASE
    ):
        markers.append((int(m.group("year")), m.start()))
    markers.sort(key=lambda x: x[1])
    out: list[dt.date] = []
    for i, (year, start) in enumerate(markers):
        if year not in years:
            continue
        end = markers[i + 1][1] if i + 1 < len(markers) else len(html)
        block = html[start:end]
        for mm in CAL_MEETING_RE.finditer(block):
            month_name = mm.group("month").lower()
            if month_name not in MONTHS:
                continue
            dates = re.sub(r"\s+", "", mm.group("dates"))
            if "-" in dates:
                _d1, d2 = dates.split("-", 1)
                day_n = int(d2)
            else:
                day_n = int(dates)
            try:
                out.append(dt.date(year, MONTHS[month_name], day_n))
            except ValueError:
                continue
    return out


def fomc_timing(event_date: dt.date) -> tuple[str, dt.time | None]:
    if event_date >= FOMC_STATEMENT_TIME_CONFIDENT_FROM:
        return "during_session", FOMC_STATEMENT_TIME_ET
    return "unknown", None


def to_canonical(event_date: dt.date) -> CanonicalEvent:
    session, etime = fomc_timing(event_date)
    return CanonicalEvent(
        event_type="fomc",
        event_date=event_date,
        symbol=None,
        reference_period=None,
        release_session=session,
        event_time_et=etime,
        source=SOURCE_FOMC,
    )


def acquire_fomc_events(
    *,
    start: dt.date = COVERAGE_START,
    end: dt.date,
    session: requests.Session | None = None,
) -> list[CanonicalEvent]:
    """
    Acquire scheduled FOMC decision days from official Fed pages.

    Years 1957-2020: fomchistorical{YYYY}.htm
    Years 2021+: fomccalendars.htm
    """
    http = session or requests.Session()
    dates: list[dt.date] = []

    hist_years = range(max(start.year, 1957), min(end.year, 2020) + 1)
    for year in hist_years:
        path = f"/monetarypolicy/fomchistorical{year}.htm"
        html = fetch_text(path, session=http)
        dates.extend(parse_historical_html(html))

    cal_years = {y for y in range(max(start.year, 2021), end.year + 1)}
    if cal_years:
        html = fetch_text("/monetarypolicy/fomccalendars.htm", session=http)
        dates.extend(parse_calendars_html(html, years=cal_years))

    uniq = sorted({d for d in dates if start <= d <= end})
    return [to_canonical(d) for d in uniq]


def assert_fixture_exclusions() -> None:
    """Concrete official-source heading fixtures used in tests."""
    assert parse_historical_heading("January 29-30 Meeting - 2019") == dt.date(
        2019, 1, 30
    )
    assert parse_historical_heading("April/May 30-1 Meeting - 2019") == dt.date(
        2019, 5, 1
    )
    assert parse_historical_heading(
        "March 15 (unscheduled) Meeting - 2020"
    ) is None
    assert parse_historical_heading("March 2 (unscheduled) Meeting - 2020") is None
    assert parse_historical_heading("January 9 Conference Call - 2008") is None
    assert parse_historical_heading("March 19 (notation vote) - 2020") is None
    assert parse_historical_heading(
        "March 17-18 (cancelled) Meeting - 2020"
    ) is None
    assert parse_historical_heading("October 4 (unscheduled) - 2019") is None
