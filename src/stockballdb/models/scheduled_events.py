"""ORM mapping for scheduled_events (scheduled-event occurrence calendar)."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from stockballdb.models.base import Base


class ScheduledEvent(Base):
    """One row per scheduled event occurrence (intrinsic event facts)."""

    __tablename__ = "scheduled_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    # No FK to trading_days — event_date is a calendar occurrence date.

    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)

    reference_period: Mapped[str | None] = mapped_column(String(32), nullable=True)

    release_session: Mapped[str] = mapped_column(String(32), nullable=False)
    event_time_et: Mapped[dt.time | None] = mapped_column(Time, nullable=True)

    source: Mapped[str] = mapped_column(String(256), nullable=False)
