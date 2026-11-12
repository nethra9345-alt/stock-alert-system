"""create smart alerts history and preferences tables

Revision ID: 7a839f21c4b5
Revises: 6182668b5567
Create Date: 2026-11-12 21:43:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a839f21c4b5'
down_revision: Union[str, Sequence[str], None] = '6182668b5567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    table_names = insp.get_table_names()

    if "alert_preferences" not in table_names:
        op.create_table(
            "alert_preferences",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
            sa.Column("price_alerts_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("portfolio_alerts_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("market_event_alerts_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("volume_spike_alerts_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("min_price_change_pct", sa.Float(), server_default="4.0", nullable=False),
            sa.Column("portfolio_loss_threshold_pct", sa.Float(), server_default="5.0", nullable=False),
            sa.Column("portfolio_drawdown_threshold_pct", sa.Float(), server_default="8.0", nullable=False),
            sa.Column("cooldown_minutes", sa.Integer(), server_default="60", nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_alert_preferences_user_id", "alert_preferences", ["user_id"])

    if "alert_history" not in table_names:
        op.create_table(
            "alert_history",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("alert_id", sa.Integer(), sa.ForeignKey("price_alerts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("symbol", sa.String(length=50), nullable=True),
            sa.Column("alert_type", sa.String(length=50), nullable=False),
            sa.Column("severity", sa.String(length=20), server_default="WARNING", nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("trigger_value", sa.Float(), nullable=True),
            sa.Column("threshold_value", sa.Float(), nullable=True),
            sa.Column("status", sa.String(length=20), server_default="TRIGGERED", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_alert_history_user_id", "alert_history", ["user_id"])
        op.create_index("ix_alert_history_symbol", "alert_history", ["symbol"])
        op.create_index("ix_alert_history_status", "alert_history", ["status"])
        op.create_index("ix_alert_history_created_at", "alert_history", ["created_at"])


def downgrade() -> None:
    op.drop_table("alert_history")
    op.drop_table("alert_preferences")
