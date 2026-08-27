"""create_asset_regimes

Revision ID: c3a91f0e2b7d
Revises: b8ed4f8d4839
Create Date: 2026-08-27 20:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3a91f0e2b7d"
down_revision: Union[str, None] = "b8ed4f8d4839"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asset_regimes",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("return_5d", sa.Numeric(), nullable=True),
        sa.Column("return_20d", sa.Numeric(), nullable=True),
        sa.Column("return_60d", sa.Numeric(), nullable=True),
        sa.Column("above_20dma", sa.Boolean(), nullable=True),
        sa.Column("above_50dma", sa.Boolean(), nullable=True),
        sa.Column("above_200dma", sa.Boolean(), nullable=True),
        sa.Column("distance_20dma_pct", sa.Numeric(), nullable=True),
        sa.Column("distance_50dma_pct", sa.Numeric(), nullable=True),
        sa.Column("distance_200dma_pct", sa.Numeric(), nullable=True),
        sa.Column("volatility_20d", sa.Numeric(), nullable=True),
        sa.Column("drawdown_pct", sa.Numeric(), nullable=True),
        sa.Column("trend_regime", sa.String(length=32), nullable=True),
        sa.Column("momentum_regime", sa.String(length=32), nullable=True),
        sa.Column("volatility_regime", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(
            ["date"], ["trading_days.date"], name="fk_asset_regimes_date"
        ),
        sa.PrimaryKeyConstraint("date", "symbol", name="pk_asset_regimes"),
    )
    op.create_index(
        "ix_asset_regimes_symbol_date",
        "asset_regimes",
        ["symbol", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_asset_regimes_symbol_date", table_name="asset_regimes")
    op.drop_table("asset_regimes")
