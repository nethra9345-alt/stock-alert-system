import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, default=1)
    symbol = Column(String(50), nullable=False, index=True)
    company_name = Column(String(200), nullable=True)
    exchange = Column(String(20), default="NSE")
    transaction_type = Column(String(10), default="BUY")  # BUY or SELL
    quantity = Column(Float, nullable=False)
    purchase_price = Column(Float, nullable=False)
    transaction_date = Column(DateTime, default=datetime.datetime.utcnow)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="portfolio_items")

