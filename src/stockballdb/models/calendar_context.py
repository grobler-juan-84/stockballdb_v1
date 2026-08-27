"""ORM mapping for calendar_context (trading-day calendar geometry)."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from stockballdb.models.base import Base


class CalendarContext(Base):
    """One row per trading day of holiday/session/transition/event context."""

    __tablename__ = "calendar_context"

    date: Mapped[dt.date] = mapped_column(
        Date,
        ForeignKey("trading_days.date", name="fk_calendar_context_date"),
        primary_key=True,
    )

    is_day_before_holiday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_day_after_holiday: Mapped[bool] = mapped_column(Boolean, nullable=False)
    holiday_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    holiday_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    is_shortened_trading_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_shortened_week: Mapped[bool] = mapped_column(Boolean, nullable=False)
    trading_days_in_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    is_turn_of_month: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_quarter_transition: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_year_transition: Mapped[bool] = mapped_column(Boolean, nullable=False)

    is_fomc_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    days_since_last_fomc: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    is_cpi_release_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    days_since_last_cpi: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    is_employment_situation_day: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )
    days_since_last_employment_situation: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )

    is_election_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    days_since_last_election: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
