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
        CheckConstraint(
            "(high IS NULL AND low IS NULL) OR "
            "(high IS NOT NULL AND low IS NOT NULL AND high >= low)",
            name="ck_daily_market_data_high_ge_low",
        ),
        CheckConstraint(
            "(adj_high IS NULL AND adj_low IS NULL) OR "
            "(adj_high IS NOT NULL AND adj_low IS NOT NULL AND adj_high >= adj_low)",
            name="ck_daily_market_data_adj_high_ge_adj_low",
        ),
        CheckConstraint(
            "volume IS NULL OR volume >= 0",
            name="ck_daily_market_data_volume_ge_0",
        ),
        CheckConstraint(
            "adj_volume IS NULL OR adj_volume >= 0",
            name="ck_daily_market_data_adj_volume_ge_0",
        ),
        CheckConstraint(
            "("
            "open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL "
            "AND volume IS NOT NULL AND adj_open IS NOT NULL AND adj_high IS NOT NULL "
            "AND adj_low IS NOT NULL AND adj_close IS NOT NULL AND adj_volume IS NOT NULL "
            "AND dividend_cash IS NOT NULL AND split_factor IS NOT NULL"
            ") OR ("
            "open IS NULL AND high IS NULL AND low IS NULL AND volume IS NULL "
            "AND adj_open IS NULL AND adj_high IS NULL AND adj_low IS NULL "
            "AND adj_close IS NULL AND adj_volume IS NULL "
            "AND dividend_cash IS NULL AND split_factor IS NULL"
            ")",
            name="ck_daily_market_data_observation_shape",
        ),
    )

    date: Mapped[dt.date] = mapped_column(
        Date,
        ForeignKey("trading_days.date", name="fk_daily_market_data_date"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)

    open: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    close: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    adj_open: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    adj_high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    adj_low: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    adj_close: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    adj_volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    dividend_cash: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    split_factor: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    return_1d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    gap_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    intraday_return: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    range_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    drawdown_from_high: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
