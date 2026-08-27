"""Build and persist the trading_days spine."""

from __future__ import annotations

import datetime as dt

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from stockballdb.calendar.nyse import CALENDAR_START, get_nyse_valid_dates, today_ny
from stockballdb.models.trading_days import TradingDay

UPSERT_COLUMNS = (
    "weekday",
    "month",
    "quarter",
    "year",
    "day_of_month",
    "week_of_year",
    "trading_day_of_month",
    "trading_day_of_year",
    "days_to_month_end",
    "is_month_end",
    "is_quarter_end",
    "is_year_end",
    "prev_trading_date",
    "next_trading_date",
)


def derive_trading_days_frame(dates: list[dt.date]) -> pd.DataFrame:
    """Derive all trading_days columns from a sorted list of session dates."""
    columns = ["date", *UPSERT_COLUMNS]
    if not dates:
        return pd.DataFrame(columns=columns)

    ordered = sorted(dates)
    frame = pd.DataFrame({"date": ordered})

    frame["weekday"] = [d.isoweekday() for d in frame["date"]]
    frame["month"] = [d.month for d in frame["date"]]
    frame["quarter"] = [(d.month - 1) // 3 + 1 for d in frame["date"]]
    frame["year"] = [d.year for d in frame["date"]]
    frame["day_of_month"] = [d.day for d in frame["date"]]
    frame["week_of_year"] = [d.isocalendar().week for d in frame["date"]]

    frame["trading_day_of_month"] = frame.groupby(["year", "month"]).cumcount() + 1
    frame["trading_day_of_year"] = frame.groupby("year").cumcount() + 1

    month_counts = frame.groupby(["year", "month"])["date"].transform("count")
    frame["days_to_month_end"] = month_counts - frame["trading_day_of_month"]
    frame["is_month_end"] = frame["days_to_month_end"] == 0

    quarter_last = frame.groupby(["year", "quarter"])["date"].transform("max")
    frame["is_quarter_end"] = frame["date"] == quarter_last

    year_last = frame.groupby("year")["date"].transform("max")
    frame["is_year_end"] = frame["date"] == year_last

    shifted_prev = frame["date"].shift(1)
    shifted_next = frame["date"].shift(-1)
    frame["prev_trading_date"] = [
        None if pd.isna(v) else v for v in shifted_prev
    ]
    frame["next_trading_date"] = [
        None if pd.isna(v) else v for v in shifted_next
    ]

    return frame[columns]


def build_trading_days_frame(
    start: dt.date = CALENDAR_START,
    end: dt.date | None = None,
) -> pd.DataFrame:
    """Generate the full trading_days DataFrame from the NYSE calendar."""
    dates = get_nyse_valid_dates(start=start, end=end)
    return derive_trading_days_frame(dates)


def upsert_trading_days(
    engine: Engine,
    frame: pd.DataFrame,
    *,
    batch_size: int = 500,
) -> int:
    """
    Idempotently upsert trading_days rows in batches.

    Returns the number of rows submitted.
    """
    if frame.empty:
        return 0

    records = frame.to_dict(orient="records")
    with engine.begin() as conn:
        for offset in range(0, len(records), batch_size):
            batch = records[offset : offset + batch_size]
            stmt = insert(TradingDay).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=[TradingDay.date],
                set_={col: getattr(stmt.excluded, col) for col in UPSERT_COLUMNS},
            )
            conn.execute(stmt)
    return len(records)


def sync_trading_days(
    engine: Engine,
    *,
    start: dt.date = CALENDAR_START,
    end: dt.date | None = None,
) -> pd.DataFrame:
    """
    Rebuild derived calendar through ``end`` and upsert into PostgreSQL.

    Recomputes the full in-memory spine then upserts — safe to rerun.
    Removes any persisted rows outside ``[start, end]``.
    """
    if end is None:
        end = today_ny()
    frame = build_trading_days_frame(start=start, end=end)
    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM trading_days "
                "WHERE date < :start_date OR date > :end_date"
            ),
            {"start_date": start, "end_date": end},
        )
    upsert_trading_days(engine, frame)
    return frame
