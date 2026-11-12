"""create market_events table

Revision ID: 6182668b5567
Revises: da20de5dab0f
Create Date: 2026-11-12 21:19:14.455676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6182668b5567'
down_revision: Union[str, Sequence[str], None] = 'da20de5dab0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use bind to check if table already created by Base.metadata.create_all
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "market_events" not in insp.get_table_names():
        op.create_table(
            "market_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol", sa.String(length=50), nullable=False),
            sa.Column("company_name", sa.String(length=200), nullable=True),
            sa.Column("event_date", sa.String(length=20), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False, server_default="NORMAL"),
            sa.Column("price_change_pct", sa.Float(), nullable=False),
            sa.Column("volume_ratio", sa.Float(), nullable=False),
            sa.Column("intraday_range_pct", sa.Float(), nullable=False),
            sa.Column("open_price", sa.Float(), nullable=False),
            sa.Column("high_price", sa.Float(), nullable=False),
            sa.Column("low_price", sa.Float(), nullable=False),
            sa.Column("close_price", sa.Float(), nullable=False),
            sa.Column("volume", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("explanation_summary", sa.Text(), nullable=True),
            sa.Column("explanation_detail", sa.Text(), nullable=True),
            sa.Column("sources", sa.JSON(), nullable=True),
            sa.Column("is_verified", sa.Boolean(), nullable=True, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("symbol", "event_type", "event_date", name="uq_symbol_event_date_type")
        )
        op.create_index(op.f("ix_market_events_id"), "market_events", ["id"], unique=False)
        op.create_index(op.f("ix_market_events_symbol"), "market_events", ["symbol"], unique=False)
        op.create_index(op.f("ix_market_events_event_date"), "market_events", ["event_date"], unique=False)
        op.create_index(op.f("ix_market_events_event_type"), "market_events", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_table("market_events")
