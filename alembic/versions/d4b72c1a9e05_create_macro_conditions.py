"""create_macro_conditions

Revision ID: d4b72c1a9e05
Revises: c3a91f0e2b7d
Create Date: 2026-08-27 21:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4b72c1a9e05"
down_revision: Union[str, None] = "c3a91f0e2b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "macro_conditions",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("inflation_rate", sa.Numeric(), nullable=True),
        sa.Column("core_inflation_rate", sa.Numeric(), nullable=True),
        sa.Column("unemployment_rate", sa.Numeric(), nullable=True),
        sa.Column("jobless_claims", sa.Numeric(), nullable=True),
        sa.Column("fed_funds_rate", sa.Numeric(), nullable=True),
        sa.Column("treasury_2y_yield", sa.Numeric(), nullable=True),
        sa.Column("treasury_10y_yield", sa.Numeric(), nullable=True),
        sa.Column("yield_curve_10y_2y", sa.Numeric(), nullable=True),
        sa.Column("fed_balance_sheet", sa.Numeric(), nullable=True),
        sa.Column("credit_spread", sa.Numeric(), nullable=True),
        sa.Column("inflation_regime", sa.String(length=32), nullable=True),
        sa.Column("rate_regime", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["date"], ["trading_days.date"], name="fk_macro_conditions_date"
        ),
        sa.PrimaryKeyConstraint("date", name="pk_macro_conditions"),
    )


def downgrade() -> None:
    op.drop_table("macro_conditions")
