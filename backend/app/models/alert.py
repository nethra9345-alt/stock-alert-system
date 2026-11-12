import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, default=1)
    symbol = Column(String(50), nullable=False, index=True)  # e.g., RELIANCE.NS
    company_name = Column(String(200), nullable=True)
    target_price = Column(Float, nullable=False)
    condition = Column(String(20), nullable=False)  # "ABOVE", "BELOW", "PCT_CHANGE"
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    triggered_at = Column(DateTime, nullable=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="alerts")


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, default=1)
    alert_id = Column(Integer, ForeignKey("price_alerts.id", ondelete="SET NULL"), nullable=True)
    symbol = Column(String(50), nullable=True, index=True)
    alert_type = Column(String(50), nullable=False, index=True)
    # Types: PRICE_ABOVE, PRICE_BELOW, PRICE_PCT_CHANGE, PORTFOLIO_LOSS, PORTFOLIO_DRAWDOWN, MARKET_EVENT, VOLUME_SPIKE
    severity = Column(String(20), default="WARNING")  # INFO, WARNING, CRITICAL
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    trigger_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    status = Column(String(20), default="TRIGGERED", index=True)  # TRIGGERED, ACKNOWLEDGED, RESOLVED
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="alert_history_items")
    alert = relationship("PriceAlert")


class AlertPreferences(Base):
    __tablename__ = "alert_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True, default=1)
    price_alerts_enabled = Column(Boolean, default=True)
    portfolio_alerts_enabled = Column(Boolean, default=True)
    market_event_alerts_enabled = Column(Boolean, default=True)
    volume_spike_alerts_enabled = Column(Boolean, default=True)
    min_price_change_pct = Column(Float, default=4.0)
    portfolio_loss_threshold_pct = Column(Float, default=5.0)
    portfolio_drawdown_threshold_pct = Column(Float, default=8.0)
    cooldown_minutes = Column(Integer, default=60)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", backref="alert_preferences_setting", uselist=False)


