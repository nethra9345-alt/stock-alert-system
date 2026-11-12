import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, default=1)
    symbol = Column(String(50), nullable=False, index=True)  # e.g., RELIANCE.NS, TCS.NS
    company_name = Column(String(200), nullable=True)
    exchange = Column(String(20), default="NSE")             # NSE / BSE
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='uq_user_symbol'),
    )

    user = relationship("User", back_populates="watchlists")

