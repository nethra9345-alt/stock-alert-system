import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    watchlists = relationship("WatchlistItem", back_populates="user", cascade="all, delete-orphan")
    portfolio_items = relationship("PortfolioTransaction", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("PriceAlert", back_populates="user", cascade="all, delete-orphan")

