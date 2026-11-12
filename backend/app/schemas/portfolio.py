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


class HoldingPerformance(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    exchange: str = "NSE"
    total_quantity: float
    avg_buy_price: float
    invested_value: float
    current_price: float
    current_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    realized_pnl: float = 0.0
    portfolio_weight_pct: float = 0.0


class StockAllocation(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    current_value: float
    weight_pct: float


class PortfolioOverview(BaseModel):
    total_invested: float
    current_portfolio_value: float
    total_pnl: float
    total_pnl_percent: float
    holdings_count: int
    holdings: List[HoldingSummary]


class PortfolioAnalyticsResponse(BaseModel):
    accounting_methodology: str
    total_invested: float
    current_portfolio_value: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    overall_return_percent: float
    active_holdings_count: int
    holdings: List[HoldingPerformance]
    allocations: List[StockAllocation]


class PortfolioAllocationResponse(BaseModel):
    total_portfolio_value: float
    active_holdings_count: int
    allocations: List[StockAllocation]
    top_holding_symbol: Optional[str] = None
    top_holding_weight_pct: float = 0.0


class PortfolioPerformanceResponse(BaseModel):
    total_invested: float
    current_portfolio_value: float
    total_realized_pnl: float
    total_unrealized_pnl: float
    overall_return_percent: float
    performance: List[HoldingPerformance]


class PortfolioRiskResponse(BaseModel):
    is_empty: bool
    insufficient_data: bool = False
    message: Optional[str] = None
    risk_score: float
    risk_level: str
    concentration: dict
    volatility: dict
    drawdown: dict
    benchmark_beta: Optional[float] = None
    has_benchmark: bool = False
    benchmark_symbol: Optional[str] = None
    sessions_analyzed: int
    disclaimer: str

