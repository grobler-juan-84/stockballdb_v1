"""ORM mapping for daily_market_data."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from stockballdb.models.base import Base


class DailyMarketData(Base):
    """One row per trading date × symbol of market observations."""

    __tablename__ = "daily_market_data"
    __table_args__ = (
        PrimaryKeyConstraint("date", "symbol", name="pk_daily_market_data"),
        Index("ix_daily_market_data_symbol_date", "symbol", "date"),
        CheckConstraint("high >= low", name="ck_daily_market_data_high_ge_low"),
        CheckConstraint("volume >= 0", name="ck_daily_market_data_volume_ge_0"),
        CheckConstraint(
            "adj_volume >= 0",
            name="ck_daily_market_data_adj_volume_ge_0",
        ),
    )

    date: Mapped[dt.date] = mapped_column(
        Date,
        ForeignKey("trading_days.date", name="fk_daily_market_data_date"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)

    open: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    adj_open: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    adj_high: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    adj_low: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    adj_close: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    adj_volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    dividend_cash: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    split_factor: Mapped[Decimal] = mapped_column(Numeric, nullable=False)

    # Phase 2A: present but unpopulated until raw/adjusted basis TBDs are locked.
    return_1d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    gap_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    intraday_return: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    range_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    drawdown_from_high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
