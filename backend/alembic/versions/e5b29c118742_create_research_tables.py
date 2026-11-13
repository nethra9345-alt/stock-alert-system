"""create research reports and chat tables

Revision ID: e5b29c118742
Revises: 7a839f21c4b5
Create Date: 2026-11-13 18:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b29c118742'
down_revision: Union[str, Sequence[str], None] = '7a839f21c4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    table_names = insp.get_table_names()

    if "research_reports" not in table_names:
        op.create_table(
            "research_reports",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("symbol", sa.String(length=50), nullable=False),
            sa.Column("company_name", sa.String(length=200), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("overview_data", sa.JSON(), nullable=True),
            sa.Column("fundamentals_data", sa.JSON(), nullable=True),
            sa.Column("technical_data", sa.JSON(), nullable=True),
            sa.Column("events_data", sa.JSON(), nullable=True),
            sa.Column("risk_factors", sa.JSON(), nullable=True),
            sa.Column("sources", sa.JSON(), nullable=True),
            sa.Column("conclusion", sa.Text(), nullable=False),
            sa.Column("pdf_path", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_research_reports_user_id", "research_reports", ["user_id"])
        op.create_index("ix_research_reports_symbol", "research_reports", ["symbol"])
        op.create_index("ix_research_reports_created_at", "research_reports", ["created_at"])

    if "research_chat_messages" not in table_names:
        op.create_table(
            "research_chat_messages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("session_id", sa.String(length=100), nullable=False),
            sa.Column("symbol", sa.String(length=50), nullable=True),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("retrieved_context", sa.JSON(), nullable=True),
            sa.Column("sources", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_research_chat_messages_user_id", "research_chat_messages", ["user_id"])
        op.create_index("ix_research_chat_messages_session_id", "research_chat_messages", ["session_id"])
        op.create_index("ix_research_chat_messages_symbol", "research_chat_messages", ["symbol"])
        op.create_index("ix_research_chat_messages_created_at", "research_chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("research_chat_messages")
    op.drop_table("research_reports")
