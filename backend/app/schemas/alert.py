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
