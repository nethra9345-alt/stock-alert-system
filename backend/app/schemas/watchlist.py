from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class WatchlistCreate(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    exchange: str = "NSE"
    notes: Optional[str] = None


class WatchlistUpdate(BaseModel):
    notes: Optional[str] = None
    company_name: Optional[str] = None


class WatchlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    symbol: str
    company_name: Optional[str] = None
    exchange: str
    notes: Optional[str] = None
    created_at: datetime
    # Current market quote enriched dynamically
    current_price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
