"""Pydantic schemas for Financial News Intelligence & Market Sentiment Analysis."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class NewsSentimentDetail(BaseModel):
    id: Optional[int] = None
    sentiment_label: str
    sentiment_score: float
    confidence: float
    ai_summary: Optional[str] = None
    key_facts: Optional[List[str]] = None
    financial_figures: Optional[List[str]] = None
    companies_mentioned: Optional[List[str]] = None
    market_relevance: Optional[str] = None
    risk_factors: Optional[List[str]] = None
    model_version: Optional[str] = None
    analyzed_at: Optional[str] = None


class NewsItemResponse(BaseModel):
    id: int
    symbol: Optional[str] = None
    company_name: Optional[str] = None
    title: str
    summary: Optional[str] = None
    source: str
    url: str
    category: str
    published_at: str
    market_session_timing: Optional[str] = None
    sentiment: Optional[NewsSentimentDetail] = None


class NewsListResponse(BaseModel):
    total: int
    items: List[NewsItemResponse]


class CompanySentimentSummaryResponse(BaseModel):
    symbol: str
    timeframe: str
    total_articles: int
    average_sentiment_score: float
    distribution: Dict[str, int]
    sentiment_trend: str
    is_insufficient_data: bool
    message: str
    recent_articles: List[Dict[str, Any]]


class SentimentTimelinePoint(BaseModel):
    date: str
    avg_sentiment_score: float
    article_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    mixed_count: int


class NewsCorrelationResponse(BaseModel):
    news_id: int
    symbol: str
    publication_timestamp: str
    market_session_timing: str
    trading_session_date: str
    price_metrics: Dict[str, Any]
    volume_metrics: Dict[str, Any]
    technical_context: Dict[str, Any]
    detected_market_events: List[Dict[str, Any]]
    correlation_disclaimer: str


class MarketNewsOverviewResponse(BaseModel):
    overall_sentiment: str
    average_score: float
    distribution: Dict[str, int]
    total_articles: int
    top_headlines: List[NewsItemResponse]
    refreshed_at: str


class NewsAlertResponse(BaseModel):
    id: int
    news_id: Optional[int] = None
    symbol: Optional[str] = None
    alert_type: str
    severity: str
    title: str
    message: str
    status: str
    created_at: Optional[str] = None

