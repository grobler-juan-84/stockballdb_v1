"""Derive calendar_context from trading_days, NYSE metadata, scheduled_events."""

from __future__ import annotations

import datetime as dt
from bisect import bisect_right

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from stockballdb.calendar_context.holidays import (
    HolidayCatalog,
    early_close_dates,
    resolve_gap_closures,
)
from stockballdb.models.calendar_context import CalendarContext

EVENT_TYPES = (
    "fomc",
    "cpi",
    "employment_situation",
    "election",
)

FLAG_COLUMNS = {
    "fomc": "is_fomc_day",
    "cpi": "is_cpi_release_day",
    "employment_situation": "is_employment_situation_day",
    "election": "is_election_day",
}

SINCE_COLUMNS = {
    "fomc": "days_since_last_fomc",
    "cpi": "days_since_last_cpi",
    "employment_situation": "days_since_last_employment_situation",
    "election": "days_since_last_election",
}

CONTEXT_COLUMNS = (
    "date",
    "is_day_before_holiday",
    "is_day_after_holiday",
    "holiday_name",
    "holiday_type",
    "is_shortened_trading_day",
    "is_shortened_week",
    "trading_days_in_week",
    "is_turn_of_month",
    "is_quarter_transition",
    "is_year_transition",
    "is_fomc_day",
    "days_since_last_fomc",
    "is_cpi_release_day",
    "days_since_last_cpi",
    "is_employment_situation_day",
    "days_since_last_employment_situation",
    "is_election_day",
    "days_since_last_election",
)


class CalendarContextValidationError(Exception):
    """Raised when calendar_context validation fails."""


def effective_session(
    event_date: dt.date,
    trading_set: set[dt.date],
    trading_days: list[dt.date],
) -> dt.date | None:
    """
    Trading-day spine anchor for days_since.

    On-calendar event → event_date.
    Off-calendar → first trading day strictly after event_date.
    """
    if event_date in trading_set:
        return event_date
    i = bisect_right(trading_days, event_date)
    if i >= len(trading_days):
        return None
    return trading_days[i]


def _load_trading_days(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT date, weekday, month, quarter, year,
                       trading_day_of_month, trading_day_of_year,
                       is_month_end, is_quarter_end, is_year_end,
                       prev_trading_date, next_trading_date
                FROM trading_days
                ORDER BY date
                """
            )
        ).mappings().all()
    if not rows:
        raise CalendarContextValidationError("trading_days is empty")
    return pd.DataFrame([dict(r) for r in rows])


def _load_events(engine: Engine) -> dict[str, list[dt.date]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT event_type, event_date
                FROM scheduled_events
                WHERE event_type IN
                  ('fomc','cpi','employment_situation','election')
                ORDER BY event_date
                """
            )
        ).all()
    out: dict[str, list[dt.date]] = {k: [] for k in EVENT_TYPES}
    for etype, edate in rows:
        out[etype].append(edate)
    return out


def derive_calendar_context_frame(
    trading: pd.DataFrame,
    events_by_type: dict[str, list[dt.date]],
    *,
    early_closes: set[dt.date] | None = None,
    catalog: HolidayCatalog | None = None,
) -> pd.DataFrame:
    """Pure derivation of calendar_context columns."""
    if trading.empty:
        return pd.DataFrame(columns=list(CONTEXT_COLUMNS))

    days = [d if isinstance(d, dt.date) else d.date() for d in trading["date"]]
    trading = trading.copy()
    trading["date"] = days
    trading_set = set(days)
    start, end = days[0], days[-1]

    if early_closes is None:
        early_closes = early_close_dates(start, end)
    if catalog is None:
        catalog = HolidayCatalog(start=start, end=end)

    # ISO week counts
    iso_keys = [d.isocalendar()[:2] for d in days]
    week_counts: dict[tuple[int, int], int] = {}
    for key in iso_keys:
        week_counts[key] = week_counts.get(key, 0) + 1

    # First trading day of quarter / year
    first_of_quarter: set[dt.date] = set()
    first_of_year: set[dt.date] = set()
    seen_q: set[tuple[int, int]] = set()
    seen_y: set[int] = set()
    for _, row in trading.iterrows():
        d = row["date"]
        yq = (int(row["year"]), int(row["quarter"]))
        y = int(row["year"])
        if yq not in seen_q:
            seen_q.add(yq)
            first_of_quarter.add(d)
        if y not in seen_y:
            seen_y.add(y)
            first_of_year.add(d)

    # Event flags and days_since
    event_dates: dict[str, set[dt.date]] = {
        k: set(v) for k, v in events_by_type.items()
    }
    effective_lists: dict[str, list[dt.date]] = {}
    for etype in EVENT_TYPES:
        effs: list[dt.date] = []
        seen_eff: set[dt.date] = set()
        for ed in sorted(events_by_type.get(etype, [])):
            eff = effective_session(ed, trading_set, days)
            if eff is None or eff in seen_eff:
                continue
            seen_eff.add(eff)
            effs.append(eff)
        effective_lists[etype] = effs

    day_index = {d: i for i, d in enumerate(days)}

    records: list[dict] = []
    for idx, row in trading.iterrows():
        d = row["date"]
        prev_d = row["prev_trading_date"]
        next_d = row["next_trading_date"]
        if prev_d is not None and not isinstance(prev_d, dt.date):
            prev_d = prev_d.date() if hasattr(prev_d, "date") else prev_d
        if next_d is not None and not isinstance(next_d, dt.date):
            next_d = next_d.date() if hasattr(next_d, "date") else next_d

        before = False
        after = False
        names_fwd: list[str] = []
        names_back: list[str] = []
        type_fwd: str | None = None
        type_back: str | None = None

        if next_d is not None:
            names_fwd, type_fwd = resolve_gap_closures(
                d, next_d, trading_set, catalog
            )
            before = bool(names_fwd)
        if prev_d is not None:
            names_back, type_back = resolve_gap_closures(
                prev_d, d, trading_set, catalog
            )
            after = bool(names_back)

        if before or after:
            ordered: list[str] = []
            seen_n: set[str] = set()
            for n in names_fwd + names_back:
                if n not in seen_n:
                    seen_n.add(n)
                    ordered.append(n)
            holiday_name = "|".join(ordered)
            types = [t for t in (type_fwd, type_back) if t]
            holiday_type = (
                "exceptional" if "exceptional" in types else "regular"
            )
        else:
            holiday_name = None
            holiday_type = None

        iso_key = d.isocalendar()[:2]
        td_in_week = week_counts[iso_key]

        rec: dict = {
            "date": d,
            "is_day_before_holiday": before,
            "is_day_after_holiday": after,
            "holiday_name": holiday_name,
            "holiday_type": holiday_type,
            "is_shortened_trading_day": d in early_closes,
            "is_shortened_week": td_in_week < 5,
            "trading_days_in_week": td_in_week,
            "is_turn_of_month": bool(row["is_month_end"])
            or int(row["trading_day_of_month"]) == 1,
            "is_quarter_transition": bool(row["is_quarter_end"])
            or d in first_of_quarter,
            "is_year_transition": bool(row["is_year_end"]) or d in first_of_year,
        }

        for etype in EVENT_TYPES:
            rec[FLAG_COLUMNS[etype]] = d in event_dates[etype]
            effs = effective_lists[etype]
            # latest effective_session <= d
            j = bisect_right(effs, d) - 1
            if j < 0:
                rec[SINCE_COLUMNS[etype]] = None
            else:
                rec[SINCE_COLUMNS[etype]] = day_index[d] - day_index[effs[j]]

        records.append(rec)

    return pd.DataFrame(records, columns=list(CONTEXT_COLUMNS))


def upsert_calendar_context(
    engine: Engine,
    frame: pd.DataFrame,
    *,
    batch_size: int = 500,
) -> int:
    if frame.empty:
        return 0
    records = frame.to_dict(orient="records")
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM calendar_context"))
        for offset in range(0, len(records), batch_size):
            batch = records[offset : offset + batch_size]
            conn.execute(insert(CalendarContext).values(batch))
    return len(records)


def sync_calendar_context(engine: Engine) -> pd.DataFrame:
    trading = _load_trading_days(engine)
    events = _load_events(engine)
    frame = derive_calendar_context_frame(trading, events)
    upsert_calendar_context(engine, frame)
    return frame
