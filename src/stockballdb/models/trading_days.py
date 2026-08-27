"""ORM mapping for the trading_days spine table."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, CheckConstraint, Date, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from stockballdb.models.base import Base


class TradingDay(Base):
    """One row per valid U.S. equity-market trading day."""

    __tablename__ = "trading_days"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 1 AND 5", name="ck_trading_days_weekday"),
        CheckConstraint("month BETWEEN 1 AND 12", name="ck_trading_days_month"),
        CheckConstraint("quarter BETWEEN 1 AND 4", name="ck_trading_days_quarter"),
        CheckConstraint(
            "day_of_month BETWEEN 1 AND 31",
            name="ck_trading_days_day_of_month",
        ),
        CheckConstraint(
            "week_of_year BETWEEN 1 AND 53",
            name="ck_trading_days_week_of_year",
        ),
        CheckConstraint(
            "trading_day_of_month >= 1",
            name="ck_trading_days_td_of_month",
        ),
        CheckConstraint(
            "trading_day_of_year >= 1",
            name="ck_trading_days_td_of_year",
        ),
        CheckConstraint(
            "days_to_month_end >= 0",
            name="ck_trading_days_days_to_month_end",
        ),
    )

    date: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    quarter: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_of_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    week_of_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    trading_day_of_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    trading_day_of_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    days_to_month_end: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_month_end: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_quarter_end: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_year_end: Mapped[bool] = mapped_column(Boolean, nullable=False)
    prev_trading_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    next_trading_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
