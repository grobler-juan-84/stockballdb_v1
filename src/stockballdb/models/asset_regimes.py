"""ORM mapping for asset_regimes (point-in-time historical asset state)."""

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


class AssetRegime(Base):
    """One row per date × symbol of historical asset-state measures and regimes."""

    __tablename__ = "asset_regimes"
    __table_args__ = (
        PrimaryKeyConstraint("date", "symbol", name="pk_asset_regimes"),
        Index("ix_asset_regimes_symbol_date", "symbol", "date"),
    )

    date: Mapped[dt.date] = mapped_column(
        Date,
        ForeignKey("trading_days.date", name="fk_asset_regimes_date"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)

    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)

    return_5d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    return_20d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    return_60d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    above_20dma: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    above_50dma: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    above_200dma: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    distance_20dma_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    distance_50dma_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    distance_200dma_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    volatility_20d: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    drawdown_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    trend_regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    momentum_regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    volatility_regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
