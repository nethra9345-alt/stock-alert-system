import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    BigInteger,
    JSON,
    UniqueConstraint
)
from backend.app.core.database import Base


class MarketEvent(Base):
    __tablename__ = "market_events"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    company_name = Column(String(200), nullable=True)
    event_date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    event_type = Column(String(50), nullable=False, index=True)  # PRICE_SURGE, GAP_UP, etc.
    severity = Column(String(20), nullable=False, default="NORMAL")  # NORMAL, ELEVATED, HIGH, EXTREME

    price_change_pct = Column(Float, nullable=False)
    volume_ratio = Column(Float, nullable=False)
    intraday_range_pct = Column(Float, nullable=False)

    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False, default=0)

    explanation_summary = Column(Text, nullable=True)
    explanation_detail = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)  # List of {title, url, publisher, published_at}
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "event_type", "event_date", name="uq_symbol_event_date_type"),
    )
