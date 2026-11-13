"""Pydantic schemas for AI Stock Research & Investment Assistant."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ResearchChatRequest(BaseModel):
    message: str = Field(..., description="User research question or prompt")
    session_id: str = Field(default="default-session", description="Session identifier for multi-turn dialogue")
    symbol: Optional[str] = Field(default=None, description="Optional target stock symbol")
    include_portfolio: bool = Field(default=False, description="Explicit authorization to incorporate user portfolio data")


class ResearchChatResponse(BaseModel):
    message_id: int
    session_id: str
    symbol: Optional[str] = None
    role: str = "assistant"
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    retrieved_context: Optional[Dict[str, Any]] = None
    provider_used: str
    created_at: str


class StockComparisonRequest(BaseModel):
    symbols: List[str] = Field(..., min_length=2, max_length=5, description="List of 2 to 5 stock ticker symbols")
    period: str = Field(default="6mo", description="Timeframe for historical series ('1mo', '3mo', '6mo', '1y')")


class CreateReportRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol to generate report for")
    title: Optional[str] = Field(default=None, description="Optional custom report title")


class ReportListItem(BaseModel):
    id: int
    symbol: str
    company_name: Optional[str] = None
    title: str
    summary: str
    created_at: Optional[str] = None
