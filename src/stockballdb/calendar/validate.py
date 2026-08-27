"""Validation for the trading_days spine."""

from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Documented NYSE full closures (must be absent from the spine).
KNOWN_CLOSED: tuple[dt.date, ...] = (
    dt.date(1985, 9, 27),  # Hurricane Gloria
    dt.date(1994, 4, 27),  # Nixon day of mourning
    dt.date(2001, 9, 11),
    dt.date(2001, 9, 12),
    dt.date(2001, 9, 13),
    dt.date(2001, 9, 14),
    dt.date(2012, 10, 29),  # Hurricane Sandy
    dt.date(2012, 10, 30),
)

# Ordinary / post-closure sessions that must be present (within range).
KNOWN_OPEN: tuple[dt.date, ...] = (
    dt.date(1960, 6, 15),
    dt.date(1980, 3, 12),
    dt.date(1985, 9, 30),  # next session after Gloria
    dt.date(2000, 8, 16),
    dt.date(2001, 9, 17),  # reopen after 9/11
    dt.date(2012, 10, 31),  # reopen after Sandy
    dt.date(2020, 4, 15),
)


class TradingDaysValidationError(Exception):
    """Raised when trading_days validation fails."""


def validate_trading_days_frame(frame: pd.DataFrame) -> None:
    """Validate an in-memory trading_days DataFrame. Raises on failure."""
    errors: list[str] = []

    if frame.empty:
        raise TradingDaysValidationError("trading_days frame is empty")

    if frame["date"].duplicated().any():
        errors.append("duplicate dates")

    if not frame["date"].is_monotonic_increasing:
        errors.append("dates are not ascending")

    weekdays = frame["date"].map(lambda d: d.isoweekday())
    if (weekdays > 5).any():
        errors.append("weekend dates present")

    date_set = set(frame["date"].tolist())
    min_d = frame["date"].iloc[0]
    max_d = frame["date"].iloc[-1]

    for closed in KNOWN_CLOSED:
        if min_d <= closed <= max_d and closed in date_set:
            errors.append(f"known closure present: {closed}")

    for opened in KNOWN_OPEN:
        if min_d <= opened <= max_d and opened not in date_set:
            errors.append(f"known session missing: {opened}")

    if pd.notna(frame["prev_trading_date"].iloc[0]):
        errors.append("first row prev_trading_date must be NULL")
    if pd.notna(frame["next_trading_date"].iloc[-1]):
        errors.append("last row next_trading_date must be NULL")

    prev_ok = (
        frame["prev_trading_date"].iloc[1:].reset_index(drop=True)
        == frame["date"].iloc[:-1].reset_index(drop=True)
    ).all()
    next_ok = (
        frame["next_trading_date"].iloc[:-1].reset_index(drop=True)
        == frame["date"].iloc[1:].reset_index(drop=True)
    ).all()
    if not prev_ok:
        errors.append("prev_trading_date chain broken")
    if not next_ok:
        errors.append("next_trading_date chain broken")

    if not (frame["days_to_month_end"] == 0).equals(frame["is_month_end"]):
        errors.append("days_to_month_end / is_month_end mismatch")

    if (frame["weekday"] != weekdays).any():
        errors.append("weekday does not match ISO weekday")

    iso_weeks = frame["date"].map(lambda d: d.isocalendar().week)
    if (frame["week_of_year"] != iso_weeks).any():
        errors.append("week_of_year is not ISO 8601")

    # trading_day_of_month / year restart checks
    for _, group in frame.groupby(["year", "month"]):
        expected = list(range(1, len(group) + 1))
        if group["trading_day_of_month"].tolist() != expected:
            errors.append("trading_day_of_month numbering incorrect")
            break

    for _, group in frame.groupby("year"):
        expected = list(range(1, len(group) + 1))
        if group["trading_day_of_year"].tolist() != expected:
            errors.append("trading_day_of_year numbering incorrect")
            break

    for _, group in frame.groupby(["year", "quarter"]):
        last = group.iloc[-1]
        if not bool(last["is_quarter_end"]):
            errors.append(f"missing is_quarter_end on {last['date']}")
            break
        if group["is_quarter_end"].sum() != 1:
            errors.append("is_quarter_end count != 1 within a quarter")
            break

    for _, group in frame.groupby("year"):
        if group["is_year_end"].sum() != 1:
            errors.append("is_year_end count != 1 within a year")
            break

    if errors:
        raise TradingDaysValidationError("; ".join(errors))


def validate_trading_days_db(engine: Engine, expected_count: int) -> None:
    """Validate trading_days rows in PostgreSQL."""
    errors: list[str] = []
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM trading_days")).scalar_one()
        if count != expected_count:
            errors.append(f"row count {count} != expected {expected_count}")

        null_prev = conn.execute(
            text("SELECT COUNT(*) FROM trading_days WHERE prev_trading_date IS NULL")
        ).scalar_one()
        null_next = conn.execute(
            text("SELECT COUNT(*) FROM trading_days WHERE next_trading_date IS NULL")
        ).scalar_one()
        if null_prev != 1:
            errors.append(f"expected 1 NULL prev_trading_date, found {null_prev}")
        if null_next != 1:
            errors.append(f"expected 1 NULL next_trading_date, found {null_next}")

        weekends = conn.execute(
            text(
                "SELECT COUNT(*) FROM trading_days "
                "WHERE EXTRACT(ISODOW FROM date) > 5"
            )
        ).scalar_one()
        if weekends:
            errors.append(f"weekend rows in database: {weekends}")

        dupes = conn.execute(
            text(
                "SELECT COUNT(*) FROM ("
                "SELECT date FROM trading_days GROUP BY date HAVING COUNT(*) > 1"
                ") d"
            )
        ).scalar_one()
        if dupes:
            errors.append("duplicate primary keys")

    if errors:
        raise TradingDaysValidationError("; ".join(errors))
