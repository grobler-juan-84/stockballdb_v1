"""ORM mapping for macro_conditions (trading-day macro context)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from stockballdb.models.base import Base


class MacroCondition(Base):
    """One row per trading day of macroeconomic / monetary context."""

    __tablename__ = "macro_conditions"
    __table_args__ = (
        PrimaryKeyConstraint("date", name="pk_macro_conditions"),
    )

    date: Mapped[dt.date] = mapped_column(
        Date,
        ForeignKey("trading_days.date", name="fk_macro_conditions_date"),
        nullable=False,
    )

    inflation_rate: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    core_inflation_rate: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    unemployment_rate: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    jobless_claims: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    fed_funds_rate: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    treasury_2y_yield: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    treasury_10y_yield: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    yield_curve_10y_2y: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    fed_balance_sheet: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    credit_spread: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)

    # pmi deferred from V1 — column intentionally omitted

    inflation_regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rate_regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
