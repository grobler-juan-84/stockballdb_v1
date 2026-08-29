"""daily_market_data close-only nullable OHLC

Revision ID: a8f3c2d1b4e5
Revises: f6d94c3e5b27
Create Date: 2026-08-28 19:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f3c2d1b4e5"
down_revision: Union[str, None] = "f6d94c3e5b27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_daily_market_data_high_ge_low",
        "daily_market_data",
        type_="check",
    )
    op.drop_constraint(
        "ck_daily_market_data_volume_ge_0",
        "daily_market_data",
        type_="check",
    )
    op.drop_constraint(
        "ck_daily_market_data_adj_volume_ge_0",
        "daily_market_data",
        type_="check",
    )

    for col in (
        "open",
        "high",
        "low",
        "volume",
        "adj_open",
        "adj_high",
        "adj_low",
        "adj_close",
        "adj_volume",
        "dividend_cash",
        "split_factor",
    ):
        op.alter_column("daily_market_data", col, nullable=True)

    op.create_check_constraint(
        "ck_daily_market_data_volume_ge_0",
        "daily_market_data",
        "volume IS NULL OR volume >= 0",
    )
    op.create_check_constraint(
        "ck_daily_market_data_adj_volume_ge_0",
        "daily_market_data",
        "adj_volume IS NULL OR adj_volume >= 0",
    )
    op.create_check_constraint(
        "ck_daily_market_data_high_ge_low",
        "daily_market_data",
        "(high IS NULL AND low IS NULL) OR (high IS NOT NULL AND low IS NOT NULL AND high >= low)",
    )
    op.create_check_constraint(
        "ck_daily_market_data_adj_high_ge_adj_low",
        "daily_market_data",
        "(adj_high IS NULL AND adj_low IS NULL) OR "
        "(adj_high IS NOT NULL AND adj_low IS NOT NULL AND adj_high >= adj_low)",
    )
    op.create_check_constraint(
        "ck_daily_market_data_observation_shape",
        "daily_market_data",
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
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_daily_market_data_observation_shape",
        "daily_market_data",
        type_="check",
    )
    op.drop_constraint(
        "ck_daily_market_data_adj_high_ge_adj_low",
        "daily_market_data",
        type_="check",
    )
    op.drop_constraint(
        "ck_daily_market_data_high_ge_low",
        "daily_market_data",
        type_="check",
    )
    op.drop_constraint(
        "ck_daily_market_data_adj_volume_ge_0",
        "daily_market_data",
        type_="check",
    )
    op.drop_constraint(
        "ck_daily_market_data_volume_ge_0",
        "daily_market_data",
        type_="check",
    )

    for col in (
        "open",
        "high",
        "low",
        "volume",
        "adj_open",
        "adj_high",
        "adj_low",
        "adj_close",
        "adj_volume",
        "dividend_cash",
        "split_factor",
    ):
        op.alter_column("daily_market_data", col, nullable=False)

    op.create_check_constraint(
        "ck_daily_market_data_high_ge_low",
        "daily_market_data",
        "high >= low",
    )
    op.create_check_constraint(
        "ck_daily_market_data_volume_ge_0",
        "daily_market_data",
        "volume >= 0",
    )
    op.create_check_constraint(
        "ck_daily_market_data_adj_volume_ge_0",
        "daily_market_data",
        "adj_volume >= 0",
    )
