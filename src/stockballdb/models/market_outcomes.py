"""ORM mapping for market_outcomes (retrospective forward labels)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from stockballdb.models.base import Base


class MarketOutcome(Base):
    """One row per date × symbol of retrospective forward outcomes."""

    __tablename__ = "market_outcomes"
    __table_args__ = (
        PrimaryKeyConstraint("date", "symbol", name="pk_market_outcomes"),
        Index("ix_market_outcomes_symbol_date", "symbol", "date"),
    )

    date: Mapped[dt.date] = mapped_column(
        Date,
        ForeignKey("trading_days.date", name="fk_market_outcomes_date"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)

    return_1d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    return_3d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    return_5d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    return_10d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    return_20d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    max_up_5d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    max_down_5d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    max_up_20d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    max_down_20d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    positive_1d: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    positive_5d: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    positive_20d: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
