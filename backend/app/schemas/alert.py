from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AlertCreate(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    target_price: float
    condition: str = Field(description="ABOVE or BELOW")
    notes: Optional[str] = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    symbol: str
    company_name: Optional[str] = None
    target_price: float
    condition: str
    is_active: bool
    is_triggered: bool
    triggered_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    current_price: Optional[float] = None


class AlertHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    alert_id: Optional[int] = None
    symbol: Optional[str] = None
    alert_type: str
    severity: str
    title: str
    message: str
    trigger_value: Optional[float] = None
    threshold_value: Optional[float] = None
    status: str
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class AlertPreferencesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    price_alerts_enabled: bool
    portfolio_alerts_enabled: bool
    market_event_alerts_enabled: bool
    volume_spike_alerts_enabled: bool
    min_price_change_pct: float
    portfolio_loss_threshold_pct: float
    portfolio_drawdown_threshold_pct: float
    cooldown_minutes: int
    updated_at: datetime


class AlertPreferencesUpdate(BaseModel):
    price_alerts_enabled: Optional[bool] = None
    portfolio_alerts_enabled: Optional[bool] = None
    market_event_alerts_enabled: Optional[bool] = None
    volume_spike_alerts_enabled: Optional[bool] = None
    min_price_change_pct: Optional[float] = None
    portfolio_loss_threshold_pct: Optional[float] = None
    portfolio_drawdown_threshold_pct: Optional[float] = None
    cooldown_minutes: Optional[int] = None


class AlertEvaluateResponse(BaseModel):
    evaluated_at: datetime
    new_alerts_triggered_count: int
    alerts: list[AlertHistoryItem]

