"""API Endpoints for Stage 8: Financial News Intelligence & Market Sentiment Analysis."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.models.news import FinancialNews, NewsSentiment, CompanySentimentDaily, NewsAlert
from backend.app.schemas.news import (
    NewsItemResponse,
    NewsListResponse,
    CompanySentimentSummaryResponse,
    SentimentTimelinePoint,
    NewsCorrelationResponse,
    MarketNewsOverviewResponse,
    NewsAlertResponse,
    NewsSentimentDetail,
)
from backend.app.services.market_service import normalize_symbol
from backend.app.services.news_aggregator import (
    fetch_news_for_symbol,
    sync_news_to_database,
    refresh_news_for_tracked_stocks,
)
from backend.app.services.news_sentiment import (
    analyze_and_persist_news_sentiment,
    analyze_article_content,
)
from backend.app.services.news_analytics import (
    calculate_company_sentiment_summary,
    get_sentiment_trends_timeline,
    analyze_news_price_correlation,
)
from backend.app.services.news_alerts import (
    evaluate_news_alerts_for_user,
    get_user_news_alerts,
)

router = APIRouter()


def _format_news_item(fn: FinancialNews, ns: Optional[NewsSentiment] = None) -> Dict[str, Any]:
    sent_dict = None
    if ns:
        sent_dict = {
            "id": ns.id,
            "sentiment_label": ns.sentiment_label,
            "sentiment_score": ns.sentiment_score,
            "confidence": ns.confidence,
            "ai_summary": ns.ai_summary,
            "key_facts": ns.key_facts,
            "financial_figures": ns.financial_figures,
            "companies_mentioned": ns.companies_mentioned,
            "market_relevance": ns.market_relevance,
            "risk_factors": ns.risk_factors,
            "model_version": ns.model_version,
            "analyzed_at": ns.analyzed_at.isoformat() + "Z" if ns.analyzed_at else None,
        }
    return {
        "id": fn.id,
        "symbol": fn.symbol,
        "company_name": fn.company_name,
        "title": fn.title,
        "summary": fn.summary,
        "source": fn.source,
        "url": fn.url,
        "category": fn.category or "MARKET",
        "published_at": fn.published_at.isoformat() + "Z" if fn.published_at else "",
        "market_session_timing": fn.market_session_timing,
        "sentiment": sent_dict,
    }


@router.get("", response_model=NewsListResponse)
def list_financial_news(
    symbol: Optional[str] = Query(None, description="Optional symbol filter"),
    category: Optional[str] = Query(None, description="Optional category filter (EARNINGS, REGULATORY, etc.)"),
    sentiment_label: Optional[str] = Query(None, description="POSITIVE, NEGATIVE, NEUTRAL, MIXED"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieves paginated financial news articles with optional filters."""
    query = db.query(FinancialNews, NewsSentiment).outerjoin(NewsSentiment, FinancialNews.id == NewsSentiment.news_id)

    if symbol:
        norm_sym = normalize_symbol(symbol)
        query = query.filter((FinancialNews.symbol == norm_sym) | (NewsSentiment.symbol == norm_sym))

    if category:
        query = query.filter(FinancialNews.category == category.upper())

    if sentiment_label:
        query = query.filter(NewsSentiment.sentiment_label == sentiment_label.upper())

    total = query.count()
    records = query.order_by(FinancialNews.published_at.desc()).offset(offset).limit(limit).all()

    items = [_format_news_item(fn, ns) for fn, ns in records]
    return {"total": total, "items": items}


@router.get("/market/overview", response_model=MarketNewsOverviewResponse)
def get_market_news_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Returns market-wide sentiment overview and recent top financial headlines."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    records = (
        db.query(FinancialNews, NewsSentiment)
        .outerjoin(NewsSentiment, FinancialNews.id == NewsSentiment.news_id)
        .filter(FinancialNews.published_at >= cutoff)
        .order_by(FinancialNews.published_at.desc())
        .limit(50)
        .all()
    )

    distribution = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    scores: List[float] = []

    for _, ns in records:
        if ns:
            lbl = ns.sentiment_label.lower()
            distribution[lbl] = distribution.get(lbl, 0) + 1
            scores.append(ns.sentiment_score)
        else:
            distribution["neutral"] += 1

    total = len(records)
    avg_score = round(float(sum(scores) / len(scores)), 2) if scores else 0.0

    if avg_score > 0.15:
        overall = "POSITIVE"
    elif avg_score < -0.15:
        overall = "NEGATIVE"
    else:
        overall = "NEUTRAL"

    top_headlines = [_format_news_item(fn, ns) for fn, ns in records[:10]]

    return {
        "overall_sentiment": overall,
        "average_score": avg_score,
        "distribution": distribution,
        "total_articles": total,
        "top_headlines": top_headlines,
        "refreshed_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/symbol/{symbol}", response_model=NewsListResponse)
def get_news_for_symbol_endpoint(
    symbol: str,
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieves verified news articles for a specific stock ticker."""
    norm_sym = normalize_symbol(symbol)
    records = (
        db.query(FinancialNews, NewsSentiment)
        .outerjoin(NewsSentiment, FinancialNews.id == NewsSentiment.news_id)
        .filter((FinancialNews.symbol == norm_sym) | (NewsSentiment.symbol == norm_sym))
        .order_by(FinancialNews.published_at.desc())
        .limit(limit)
        .all()
    )
    items = [_format_news_item(fn, ns) for fn, ns in records]
    return {"total": len(items), "items": items}


@router.get("/sentiment/{symbol}", response_model=CompanySentimentSummaryResponse)
def get_company_sentiment_endpoint(
    symbol: str,
    timeframe: str = Query("7d", description="Timeframe ('1d', '7d', '30d')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieves company-wise sentiment distribution, average score, and trend."""
    return calculate_company_sentiment_summary(db=db, symbol=symbol, timeframe=timeframe)


@router.get("/sentiment/trends/{symbol}", response_model=List[SentimentTimelinePoint])
def get_sentiment_trends_endpoint(
    symbol: str,
    days: int = Query(14, ge=3, le=60),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Returns daily sentiment timeline data points for interactive trend charts."""
    return get_sentiment_trends_timeline(db=db, symbol=symbol, days=days)


@router.get("/correlation/{news_id}", response_model=NewsCorrelationResponse)
def get_news_correlation_endpoint(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Evaluates stock price and volume movements surrounding article publication."""
    res = analyze_news_price_correlation(db=db, news_id=news_id)
    if "error" in res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=res["error"])
    return res


@router.get("/alerts", response_model=List[NewsAlertResponse])
def get_news_alerts_endpoint(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Retrieves news alerts for the current user."""
    return get_user_news_alerts(db=db, user_id=current_user.id, limit=limit)


@router.post("/refresh")
def refresh_news_endpoint(
    symbols: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetches latest articles from news wire and analyzes sentiment for new records."""
    summary = refresh_news_for_tracked_stocks(db=db, symbols=symbols)

    # Automatically run sentiment analysis for unanalyzed news
    unanalyzed = (
        db.query(FinancialNews)
        .outerjoin(NewsSentiment, FinancialNews.id == NewsSentiment.news_id)
        .filter(NewsSentiment.id == None)
        .limit(25)
        .all()
    )
    for fn in unanalyzed:
        try:
            analyze_and_persist_news_sentiment(db, fn.id, fn.symbol)
        except Exception:
            pass

    # Evaluate new alerts for current user
    try:
        evaluate_news_alerts_for_user(db=db, user_id=current_user.id)
    except Exception:
        pass

    return summary


@router.post("/analyze/{news_id}", response_model=NewsItemResponse)
def analyze_news_article_endpoint(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Triggers or recalculates AI summarization and sentiment analysis for an article."""
    fn = db.query(FinancialNews).filter(FinancialNews.id == news_id).first()
    if not fn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial news record not found")

    ns = analyze_and_persist_news_sentiment(db=db, news_id=news_id, target_symbol=fn.symbol)
    return _format_news_item(fn, ns)


@router.get("/{news_id}", response_model=NewsItemResponse)
def get_news_detail_endpoint(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieves single news article with full AI sentiment, key facts, and figures."""
    fn = db.query(FinancialNews).filter(FinancialNews.id == news_id).first()
    if not fn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial news record not found")

    ns = db.query(NewsSentiment).filter(NewsSentiment.news_id == news_id).first()
    if not ns:
        ns = analyze_and_persist_news_sentiment(db=db, news_id=news_id, target_symbol=fn.symbol)

    return _format_news_item(fn, ns)
