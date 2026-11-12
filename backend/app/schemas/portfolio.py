from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PortfolioTransactionCreate(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    exchange: str = "NSE"
    transaction_type: str = Field(default="BUY", description="BUY or SELL")
    quantity: float
    purchase_price: float
    transaction_date: Optional[datetime] = None
    notes: Optional[str] = None


class PortfolioTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    symbol: str
    company_name: Optional[str] = None
    exchange: str
    transaction_type: str
    quantity: float
    purchase_price: float
    transaction_date: datetime
    notes: Optional[str] = None
    created_at: datetime


class HoldingSummary(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    exchange: str
    total_quantity: float
    avg_buy_price: float
    invested_value: float
    current_price: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float


class PortfolioOverview(BaseModel):
    total_invested: float
    current_portfolio_value: float
    total_pnl: float
    total_pnl_percent: float
    holdings_count: int
    holdings: List[HoldingSummary]
