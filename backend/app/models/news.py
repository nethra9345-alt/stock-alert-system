import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class FinancialNews(Base):
    __tablename__ = "financial_news"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=True, index=True)
    company_name = Column(String(200), nullable=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    url = Column(String(1000), nullable=False)
    canonical_url = Column(String(1000), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    category = Column(String(50), default="MARKET", index=True)
    published_at = Column(DateTime, nullable=False, index=True)
    retrieved_at = Column(DateTime, default=datetime.datetime.utcnow)
    market_session_timing = Column(String(20), nullable=True)  # PRE_MARKET, MARKET_HOURS, POST_MARKET, WEEKEND
    raw_snippet = Column(Text, nullable=True)

    sentiments = relationship("NewsSentiment", back_populates="news", cascade="all, delete-orphan")
    alerts = relationship("NewsAlert", back_populates="news")


class NewsSentiment(Base):
    __tablename__ = "news_sentiment"

    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, ForeignKey("financial_news.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(50), nullable=True, index=True)
    sentiment_label = Column(String(20), nullable=False)  # POSITIVE, NEGATIVE, NEUTRAL, MIXED
    sentiment_score = Column(Float, nullable=False)  # -1.0 to +1.0
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    ai_summary = Column(Text, nullable=True)
    key_facts = Column(JSON, nullable=True)
    financial_figures = Column(JSON, nullable=True)
    companies_mentioned = Column(JSON, nullable=True)
    market_relevance = Column(Text, nullable=True)
    risk_factors = Column(JSON, nullable=True)
    model_version = Column(String(50), default="stockpulse-sentiment-v1")
    analyzed_at = Column(DateTime, default=datetime.datetime.utcnow)

    news = relationship("FinancialNews", back_populates="sentiments")


class CompanySentimentDaily(Base):
    __tablename__ = "company_sentiment_daily"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    avg_sentiment_score = Column(Float, nullable=False)
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    mixed_count = Column(Integer, default=0)
    total_articles = Column(Integer, default=0)
    sentiment_trend = Column(String(20), default="NEUTRAL")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_company_sentiment_symbol_date"),
    )


class NewsAlert(Base):
    __tablename__ = "news_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    news_id = Column(Integer, ForeignKey("financial_news.id"), nullable=True, index=True)
    symbol = Column(String(50), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="NORMAL")  # LOW, NORMAL, HIGH, CRITICAL
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="TRIGGERED")  # TRIGGERED, ACKNOWLEDGED, RESOLVED
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User", backref="news_alerts")
    news = relationship("FinancialNews", back_populates="alerts")
