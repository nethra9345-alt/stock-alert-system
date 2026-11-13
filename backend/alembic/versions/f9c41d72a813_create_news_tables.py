"""create financial news and sentiment tables

Revision ID: f9c41d72a813
Revises: e5b29c118742
Create Date: 2026-11-13 18:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9c41d72a813'
down_revision: Union[str, Sequence[str], None] = 'e5b29c118742'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    table_names = insp.get_table_names()

    # 1. financial_news
    if "financial_news" not in table_names:
        op.create_table(
            "financial_news",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol", sa.String(length=50), nullable=True),
            sa.Column("company_name", sa.String(length=200), nullable=True),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("source", sa.String(length=100), nullable=False),
            sa.Column("url", sa.String(length=1000), nullable=False),
            sa.Column("canonical_url", sa.String(length=1000), nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=False),
            sa.Column("retrieved_at", sa.DateTime(), nullable=True),
            sa.Column("market_session_timing", sa.String(length=20), nullable=True),
            sa.Column("raw_snippet", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_financial_news_id"), "financial_news", ["id"], unique=False)
        op.create_index(op.f("ix_financial_news_symbol"), "financial_news", ["symbol"], unique=False)
        op.create_index(op.f("ix_financial_news_canonical_url"), "financial_news", ["canonical_url"], unique=False)
        op.create_index(op.f("ix_financial_news_content_hash"), "financial_news", ["content_hash"], unique=True)
        op.create_index(op.f("ix_financial_news_category"), "financial_news", ["category"], unique=False)
        op.create_index(op.f("ix_financial_news_published_at"), "financial_news", ["published_at"], unique=False)

    # 2. news_sentiment
    if "news_sentiment" not in table_names:
        op.create_table(
            "news_sentiment",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("news_id", sa.Integer(), sa.ForeignKey("financial_news.id", ondelete="CASCADE"), nullable=False),
            sa.Column("symbol", sa.String(length=50), nullable=True),
            sa.Column("sentiment_label", sa.String(length=20), nullable=False),
            sa.Column("sentiment_score", sa.Float(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("ai_summary", sa.Text(), nullable=True),
            sa.Column("key_facts", sa.JSON(), nullable=True),
            sa.Column("financial_figures", sa.JSON(), nullable=True),
            sa.Column("companies_mentioned", sa.JSON(), nullable=True),
            sa.Column("market_relevance", sa.Text(), nullable=True),
            sa.Column("risk_factors", sa.JSON(), nullable=True),
            sa.Column("model_version", sa.String(length=50), nullable=True),
            sa.Column("analyzed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_news_sentiment_id"), "news_sentiment", ["id"], unique=False)
        op.create_index(op.f("ix_news_sentiment_news_id"), "news_sentiment", ["news_id"], unique=False)
        op.create_index(op.f("ix_news_sentiment_symbol"), "news_sentiment", ["symbol"], unique=False)

    # 3. company_sentiment_daily
    if "company_sentiment_daily" not in table_names:
        op.create_table(
            "company_sentiment_daily",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol", sa.String(length=50), nullable=False),
            sa.Column("date", sa.String(length=20), nullable=False),
            sa.Column("avg_sentiment_score", sa.Float(), nullable=False),
            sa.Column("positive_count", sa.Integer(), nullable=True),
            sa.Column("negative_count", sa.Integer(), nullable=True),
            sa.Column("neutral_count", sa.Integer(), nullable=True),
            sa.Column("mixed_count", sa.Integer(), nullable=True),
            sa.Column("total_articles", sa.Integer(), nullable=True),
            sa.Column("sentiment_trend", sa.String(length=20), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("symbol", "date", name="uq_company_sentiment_symbol_date"),
        )
        op.create_index(op.f("ix_company_sentiment_daily_id"), "company_sentiment_daily", ["id"], unique=False)
        op.create_index(op.f("ix_company_sentiment_daily_symbol"), "company_sentiment_daily", ["symbol"], unique=False)
        op.create_index(op.f("ix_company_sentiment_daily_date"), "company_sentiment_daily", ["date"], unique=False)

    # 4. news_alerts
    if "news_alerts" not in table_names:
        op.create_table(
            "news_alerts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("news_id", sa.Integer(), sa.ForeignKey("financial_news.id"), nullable=True),
            sa.Column("symbol", sa.String(length=50), nullable=True),
            sa.Column("alert_type", sa.String(length=50), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_news_alerts_id"), "news_alerts", ["id"], unique=False)
        op.create_index(op.f("ix_news_alerts_user_id"), "news_alerts", ["user_id"], unique=False)
        op.create_index(op.f("ix_news_alerts_news_id"), "news_alerts", ["news_id"], unique=False)
        op.create_index(op.f("ix_news_alerts_symbol"), "news_alerts", ["symbol"], unique=False)
        op.create_index(op.f("ix_news_alerts_created_at"), "news_alerts", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("news_alerts")
    op.drop_table("company_sentiment_daily")
    op.drop_table("news_sentiment")
    op.drop_table("financial_news")

