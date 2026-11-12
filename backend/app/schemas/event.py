import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MarketEventSource(BaseModel):
    title: str
    url: Optional[str] = None
    publisher: Optional[str] = None
    published_at: Optional[str] = None


class MarketEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    company_name: Optional[str] = None
    event_date: str
    event_type: str
    severity: str
    price_change_pct: float
    volume_ratio: float
    intraday_range_pct: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    explanation_summary: Optional[str] = None
    explanation_detail: Optional[str] = None
    sources: Optional[List[MarketEventSource]] = Field(default_factory=list)
    is_verified: bool = False
    created_at: Optional[datetime.datetime] = None


class MarketEventListResponse(BaseModel):
    count: int
    events: List[MarketEventRead]


class AnalyzeEventsRequest(BaseModel):
    period: str = Field(default="6mo", description="Historical lookback period (e.g. 1mo, 3mo, 6mo, 1y, 2y)")
    price_threshold_pct: float = Field(default=3.5, ge=1.0, le=20.0, description="Minimum daily price change % to qualify as surge/drop")
    volume_ratio_threshold: float = Field(default=2.5, ge=1.5, le=10.0, description="Minimum ratio vs 20-day historical average to qualify as volume anomaly")


class AnalyzeEventsResponse(BaseModel):
    symbol: str
    company_name: Optional[str] = None
    analyzed_sessions: int
    detected_events_count: int
    newly_persisted_count: int
    events: List[MarketEventRead]

