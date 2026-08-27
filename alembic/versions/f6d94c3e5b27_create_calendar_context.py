"""create_calendar_context

Revision ID: f6d94c3e5b27
Revises: e5c83b2d4a16
Create Date: 2026-08-27 22:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6d94c3e5b27"
down_revision: Union[str, None] = "e5c83b2d4a16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calendar_context",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_day_before_holiday", sa.Boolean(), nullable=False),
        sa.Column("is_day_after_holiday", sa.Boolean(), nullable=False),
        sa.Column("holiday_name", sa.String(length=256), nullable=True),
        sa.Column("holiday_type", sa.String(length=32), nullable=True),
        sa.Column("is_shortened_trading_day", sa.Boolean(), nullable=False),
        sa.Column("is_shortened_week", sa.Boolean(), nullable=False),
        sa.Column("trading_days_in_week", sa.SmallInteger(), nullable=False),
        sa.Column("is_turn_of_month", sa.Boolean(), nullable=False),
        sa.Column("is_quarter_transition", sa.Boolean(), nullable=False),
        sa.Column("is_year_transition", sa.Boolean(), nullable=False),
        sa.Column("is_fomc_day", sa.Boolean(), nullable=False),
        sa.Column("days_since_last_fomc", sa.SmallInteger(), nullable=True),
        sa.Column("is_cpi_release_day", sa.Boolean(), nullable=False),
        sa.Column("days_since_last_cpi", sa.SmallInteger(), nullable=True),
        sa.Column("is_employment_situation_day", sa.Boolean(), nullable=False),
        sa.Column(
            "days_since_last_employment_situation", sa.SmallInteger(), nullable=True
        ),
        sa.Column("is_election_day", sa.Boolean(), nullable=False),
        sa.Column("days_since_last_election", sa.SmallInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["date"], ["trading_days.date"], name="fk_calendar_context_date"
        ),
        sa.PrimaryKeyConstraint("date", name="pk_calendar_context"),
    )


def downgrade() -> None:
    op.drop_table("calendar_context")
