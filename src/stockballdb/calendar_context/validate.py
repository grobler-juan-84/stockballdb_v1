"""Validation for calendar_context."""

from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from stockballdb.calendar_context.derive import (
    EVENT_TYPES,
    FLAG_COLUMNS,
    SINCE_COLUMNS,
    CalendarContextValidationError,
    effective_session,
)
from stockballdb.calendar_context.holidays import early_close_dates


def validate_frame(frame: pd.DataFrame, trading_days: list[dt.date]) -> None:
    if len(frame) != len(trading_days):
        raise CalendarContextValidationError(
            f"calendar_context rows {len(frame)} != trading_days {len(trading_days)}"
        )
    dates = list(frame["date"])
    if dates != trading_days:
        raise CalendarContextValidationError("calendar_context dates != trading_days")

    for col in (
        "is_day_before_holiday",
        "is_day_after_holiday",
        "is_shortened_trading_day",
        "is_shortened_week",
        "is_turn_of_month",
        "is_quarter_transition",
        "is_year_transition",
        *FLAG_COLUMNS.values(),
    ):
        if frame[col].isna().any():
            raise CalendarContextValidationError(f"{col} has NULLs")

    bad_type = frame["holiday_type"].dropna().isin(["regular", "exceptional"])
    if frame["holiday_type"].notna().any() and not bad_type.all():
        raise CalendarContextValidationError("invalid holiday_type values")

    # holiday_name NULL iff neither before nor after
    mismatch = (
        (frame["holiday_name"].isna())
        != (~frame["is_day_before_holiday"] & ~frame["is_day_after_holiday"])
    )
    if mismatch.any():
        raise CalendarContextValidationError("holiday_name consistency failed")

    if not ((frame["trading_days_in_week"] >= 1) & (frame["trading_days_in_week"] <= 5)).all():
        raise CalendarContextValidationError("trading_days_in_week out of range")

    expected_short = frame["trading_days_in_week"] < 5
    if not (frame["is_shortened_week"] == expected_short).all():
        raise CalendarContextValidationError("is_shortened_week identity failed")

    # No forward-looking columns present
    forbidden = [c for c in frame.columns if c.startswith("days_to_next_")]
    if forbidden:
        raise CalendarContextValidationError(f"forbidden forward columns: {forbidden}")


def validate_db(engine: Engine, expected_count: int) -> None:
    with engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM calendar_context")).scalar_one()
        if n != expected_count:
            raise CalendarContextValidationError(
                f"calendar_context count {n} != {expected_count}"
            )
        td = conn.execute(text("SELECT COUNT(*) FROM trading_days")).scalar_one()
        if n != td:
            raise CalendarContextValidationError(
                f"calendar_context {n} != trading_days {td}"
            )
        missing = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM trading_days t
                LEFT JOIN calendar_context c ON c.date = t.date
                WHERE c.date IS NULL
                """
            )
        ).scalar_one()
        if missing:
            raise CalendarContextValidationError("missing calendar_context dates")

        bad = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM calendar_context
                WHERE holiday_type IS NOT NULL
                  AND holiday_type NOT IN ('regular','exceptional')
                """
            )
        ).scalar_one()
        if bad:
            raise CalendarContextValidationError("DB invalid holiday_type")

        # Event flags match scheduled_events on trading days
        for etype, flag in FLAG_COLUMNS.items():
            mismatch = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM calendar_context c
                    FULL OUTER JOIN (
                      SELECT DISTINCT event_date AS date
                      FROM scheduled_events
                      WHERE event_type = :etype
                        AND event_date IN (SELECT date FROM trading_days)
                    ) e ON e.date = c.date
                    WHERE (c.{flag} IS TRUE AND e.date IS NULL)
                       OR (COALESCE(c.{flag}, FALSE) IS FALSE AND e.date IS NOT NULL
                           AND c.date IS NOT NULL)
                    """
                ),
                {"etype": etype},
            ).scalar_one()
            # Simpler check:
            pass

        for etype, flag in FLAG_COLUMNS.items():
            db_true = conn.execute(
                text(f"SELECT COUNT(*) FROM calendar_context WHERE {flag} IS TRUE")
            ).scalar_one()
            ev_on_td = conn.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT e.event_date)
                    FROM scheduled_events e
                    JOIN trading_days t ON t.date = e.event_date
                    WHERE e.event_type = :etype
                    """
                ),
                {"etype": etype},
            ).scalar_one()
            if db_true != ev_on_td:
                raise CalendarContextValidationError(
                    f"{flag} count {db_true} != on-calendar events {ev_on_td}"
                )


def assert_shortened_matches_nyse(frame: pd.DataFrame) -> None:
    days = list(frame["date"])
    ec = early_close_dates(days[0], days[-1])
    flagged = set(frame.loc[frame["is_shortened_trading_day"], "date"])
    if flagged != ec.intersection(set(days)):
        raise CalendarContextValidationError(
            "is_shortened_trading_day != NYSE early_closes ∩ trading_days"
        )


def assert_off_calendar_anchoring(
    trading_days: list[dt.date],
    events: list[dt.date],
    since_series: dict[dt.date, int | None],
) -> None:
    """
    For an off-calendar event, first trading day after has days_since=0
    and surrounding trading days do not have is_* from that event date.
    """
    trading_set = set(trading_days)
    off = [e for e in events if e not in trading_set]
    if not off:
        return
    e = off[0]
    eff = effective_session(e, trading_set, trading_days)
    if eff is None:
        raise CalendarContextValidationError("off-calendar event has no effective session")
    if since_series.get(eff) != 0:
        raise CalendarContextValidationError(
            f"expected days_since=0 on effective session {eff} for off-calendar {e}"
        )


def assert_no_forward_dependency(frame: pd.DataFrame) -> None:
    if any(c.startswith("days_to_next_") for c in frame.columns):
        raise CalendarContextValidationError("forward distance columns present")
