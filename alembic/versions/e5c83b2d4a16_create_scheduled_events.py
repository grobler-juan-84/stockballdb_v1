"""create_scheduled_events

Revision ID: e5c83b2d4a16
Revises: d4b72c1a9e05
Create Date: 2026-08-27 21:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5c83b2d4a16"
down_revision: Union[str, None] = "d4b72c1a9e05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_events",
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("reference_period", sa.String(length=32), nullable=True),
        sa.Column("release_session", sa.String(length=32), nullable=False),
        sa.Column("event_time_et", sa.Time(), nullable=True),
        sa.Column("source", sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint("event_id", name="pk_scheduled_events"),
    )
    op.create_index(
        "ix_scheduled_events_type_date",
        "scheduled_events",
        ["event_type", "event_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_events_type_date", table_name="scheduled_events")
    op.drop_table("scheduled_events")
