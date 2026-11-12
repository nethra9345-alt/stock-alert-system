from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IndexQuote(BaseModel):
    name: str
    symbol: str
    price: float
    change: float
    change_percent: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    previous_close: Optional[float] = None
    currency: str = "INR"
    is_live: bool = False
    is_market_open: bool = False
    timestamp: str
    data_source: str = Field(description="live_api | cached | fallback")
    is_demo: bool = False


class MarketOverview(BaseModel):
    indices: List[IndexQuote]
    market_status: str  # "OPEN" or "CLOSED"
    market_message: str
    current_time_ist: str
    top_movers: Optional[List[Dict[str, Any]]] = None


class StockQuote(BaseModel):
    symbol: str
    name: str
    exchange: str = "NSE"
    price: float
    change: float
    change_percent: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    previous_close: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    sector: Optional[str] = None
    is_live: bool = False
    is_market_open: bool = False
    timestamp: str
    data_source: str = "live_api"
    is_demo: bool = False


class OHLCVPoint(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockHistory(BaseModel):
    symbol: str
    period: str
    interval: str
    count: int
    data: List[OHLCVPoint]
    data_source: str
    is_demo: bool = False


class IndicatorPoint(BaseModel):
    timestamp: str
    close: float
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None


class IndicatorSummary(BaseModel):
    current_rsi: Optional[float] = None
    rsi_signal: str = "NEUTRAL"  # OVERBOUGHT | OVERSOLD | NEUTRAL
    macd_signal: str = "NEUTRAL" # BULLISH_CROSSOVER | BEARISH_CROSSOVER | NEUTRAL
    trend_sma: str = "NEUTRAL"   # BULLISH | BEARISH | NEUTRAL
    overall_signal: str = "NEUTRAL"


class TechnicalIndicatorResponse(BaseModel):
    symbol: str
    summary: IndicatorSummary
    indicators: List[IndicatorPoint]
    data_source: str
    is_demo: bool = False
    disclaimer: str = "Experimental technical indicators for educational purposes only. Not financial advice."

