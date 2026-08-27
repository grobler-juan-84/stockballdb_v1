"""Point-in-time reconstruction from ALFRED vintage observations."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd

from stockballdb.macro.align import TradingDayIndex, map_availability_to_trading_day
from stockballdb.macro.series import ReleaseTiming


def _parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(str(value)[:10])


def _parse_value(raw: str) -> float | None:
    if raw is None or raw == "." or raw == "":
        return None
    return float(raw)


@dataclass(frozen=True)
class VintageRow:
    ref_date: dt.date
    value: float
    realtime_start: dt.date
    realtime_end: dt.date


def parse_alfred_rows(rows: list[dict]) -> list[VintageRow]:
    out: list[VintageRow] = []
    for row in rows:
        value = _parse_value(row.get("value", "."))
        if value is None:
            continue
        out.append(
            VintageRow(
                ref_date=_parse_date(row["date"]),
                value=value,
                realtime_start=_parse_date(row["realtime_start"]),
                realtime_end=_parse_date(row["realtime_end"]),
            )
        )
    return out


def as_of_value_map(vintages: list[VintageRow], as_of: dt.date) -> dict[dt.date, float]:
    """Reference-date -> value knowable on as_of (ALFRED realtime window)."""
    state: dict[dt.date, float] = {}
    for row in vintages:
        if row.realtime_start <= as_of < row.realtime_end:
            state[row.ref_date] = row.value
    return state


def yoy_from_index_state(state: dict[dt.date, float], ref: dt.date) -> float | None:
    """YoY percent from monthly index levels in a PIT state map."""
    try:
        prior = ref.replace(year=ref.year - 1)
    except ValueError:
        return None
    cur = state.get(ref)
    base = state.get(prior)
    if cur is None or base is None or base == 0:
        return None
    return (cur / base - 1.0) * 100.0


def first_print_events(
    vintages: list[VintageRow],
) -> list[tuple[dt.date, dt.date, float]]:
    """First ALFRED print per reference date: (realtime_start, ref_date, value)."""
    by_ref: dict[dt.date, VintageRow] = {}
    for row in vintages:
        prev = by_ref.get(row.ref_date)
        if prev is None or row.realtime_start < prev.realtime_start:
            by_ref[row.ref_date] = row
    events = [(row.realtime_start, row.ref_date, row.value) for row in by_ref.values()]
    events.sort(key=lambda x: (x[0], x[1]))
    return events


def _latest_reading(
    state: dict[dt.date, float], *, compute_yoy: bool
) -> float | None:
    if not state:
        return None
    latest_ref = max(state)
    if compute_yoy:
        return yoy_from_index_state(state, latest_ref)
    return state[latest_ref]


def build_pit_level_series_on_trading_days(
    vintages: list[VintageRow],
    trading_days: list[dt.date],
    timing: ReleaseTiming,
    *,
    compute_yoy: bool = False,
) -> pd.Series:
    """
    Forward-filled PIT series on trading_days.

    Recomputes only on ALFRED realtime_start calendar dates (and their
    mapped trading days), then carries the latest knowable reading forward.
    """
    td = TradingDayIndex(trading_days)
    event_cal_dates = sorted({row.realtime_start for row in vintages})

    # calendar as_of -> latest reading
    cal_readings: dict[dt.date, float | None] = {}
    for cal in event_cal_dates:
        cal_readings[cal] = _latest_reading(
            as_of_value_map(vintages, cal), compute_yoy=compute_yoy
        )

    # Map calendar availability -> trading day sparse updates (chronological)
    sparse: dict[dt.date, float] = {}
    for cal in event_cal_dates:
        reading = cal_readings[cal]
        if reading is None:
            continue
        avail = map_availability_to_trading_day(cal, timing, td)
        if avail is None:
            continue
        sparse[avail] = reading

    # Also handle revisions whose realtime_start maps to a TD: already covered.
    # Forward-fill onto spine.
    values: list[float | None] = []
    last: float | None = None
    for d in td.days:
        if d in sparse:
            last = sparse[d]
        values.append(last)
    return pd.Series(values, index=pd.Index(td.days, name="date"), dtype="float64")


def build_distinct_inflation_release_yoy(
    vintages: list[VintageRow],
    trading_days: list[dt.date],
    timing: ReleaseTiming,
) -> list[tuple[dt.date, float]]:
    """
    One YoY point per distinct monthly CPI first-release availability.

    Used as H_t for inflation_regime (not daily forward-filled duplicates).
    """
    td = TradingDayIndex(trading_days)
    events = first_print_events(vintages)
    out: list[tuple[dt.date, float]] = []
    for realtime_start, ref_date, _index_value in events:
        avail = map_availability_to_trading_day(realtime_start, timing, td)
        if avail is None:
            continue
        state = as_of_value_map(vintages, realtime_start)
        yoy = yoy_from_index_state(state, ref_date)
        if yoy is None:
            continue
        out.append((avail, yoy))
    by_day: dict[dt.date, float] = {}
    for avail, yoy in out:
        by_day[avail] = yoy
    return sorted(by_day.items(), key=lambda x: x[0])


def build_current_series_on_trading_days(
    observations: list[dict],
    trading_days: list[dt.date],
    timing: ReleaseTiming,
    *,
    forward_fill: bool,
    walcl_release_lag: bool = False,
) -> pd.Series:
    """Align current (non-vintage) FRED observations onto trading_days."""
    td = TradingDayIndex(trading_days)
    sparse: dict[dt.date, float] = {}
    for row in observations:
        value = _parse_value(row.get("value", "."))
        if value is None:
            continue
        obs_d = _parse_date(row["date"])
        if walcl_release_lag:
            release_cal = obs_d + dt.timedelta(days=1)
            avail = map_availability_to_trading_day(release_cal, "after_close", td)
        else:
            avail = map_availability_to_trading_day(obs_d, timing, td)
        if avail is None:
            continue
        sparse[avail] = value

    values: list[float | None] = []
    last: float | None = None
    for d in td.days:
        if d in sparse:
            last = sparse[d]
            values.append(last)
        elif forward_fill:
            values.append(last)
        else:
            values.append(None)
    return pd.Series(values, index=pd.Index(td.days, name="date"), dtype="float64")
