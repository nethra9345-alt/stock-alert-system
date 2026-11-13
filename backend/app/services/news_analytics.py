"""Company-Wise Sentiment Tracking & News-to-Price Correlation Engine.

Modules 4 & 5:
1. Aggregates multi-day sentiment distribution (1d, 7d, 30d) for individual NSE stocks.
2. Identifies sentiment shifts (BULLISH_SHIFT, BEARISH_SHIFT, STABLE, VOLATILE) with sample size validation.
3. Evaluates temporal news-to-price correlation, trading volume impact, indicator changes (RSI/MACD),
   and detected Stage 5 market events without look-ahead bias or false causal claims.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
import numpy as np

from backend.app.models.news import FinancialNews, NewsSentiment, CompanySentimentDaily
from backend.app.models.event import MarketEvent
from backend.app.services.market_service import normalize_symbol, get_stock_history_df
from backend.app.services.indicators import compute_technical_indicators


def calculate_company_sentiment_summary(
    db: Session,
    symbol: str,
    timeframe: str = "7d",
) -> Dict[str, Any]:
    """
    Computes company sentiment distribution, average score, and trend over a timeframe ('1d', '7d', '30d').
    Enforces minimum sample size threshold to avoid overconfidence.
    """
    norm_sym = normalize_symbol(symbol)
    now_utc = datetime.utcnow()

    days_map = {"1d": 1, "7d": 7, "30d": 30}
    days = days_map.get(timeframe, 7)
    cutoff = now_utc - timedelta(days=days)

    # Query articles with sentiments for the symbol
    records = (
        db.query(FinancialNews, NewsSentiment)
        .join(NewsSentiment, FinancialNews.id == NewsSentiment.news_id)
        .filter(
            (FinancialNews.symbol == norm_sym) | (NewsSentiment.symbol == norm_sym),
            FinancialNews.published_at >= cutoff,
        )
        .order_by(FinancialNews.published_at.desc())
        .all()
    )

    total_articles = len(records)
    if total_articles == 0:
        return {
            "symbol": norm_sym,
            "timeframe": timeframe,
            "total_articles": 0,
            "average_sentiment_score": 0.0,
            "distribution": {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0},
            "sentiment_trend": "NO_DATA",
            "is_insufficient_data": True,
            "message": f"No recent news articles detected for {norm_sym} in the last {timeframe}.",
            "recent_articles": [],
        }

    scores: List[float] = []
    distribution = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    articles_out = []

    for fn, ns in records:
        scores.append(ns.sentiment_score)
        lbl = ns.sentiment_label.lower()
        if lbl in distribution:
            distribution[lbl] += 1
        else:
            distribution["neutral"] += 1

        articles_out.append({
            "id": fn.id,
            "title": fn.title,
            "source": fn.source,
            "url": fn.url,
            "published_at": fn.published_at.isoformat() + "Z",
            "sentiment_label": ns.sentiment_label,
            "sentiment_score": ns.sentiment_score,
            "confidence": ns.confidence,
            "market_session_timing": fn.market_session_timing,
        })

    avg_score = round(float(np.mean(scores)), 2)

    # Sample size validation
    is_insufficient = total_articles < 2

    # Trend calculation
    pos_count = distribution["positive"]
    neg_count = distribution["negative"]

    if is_insufficient:
        trend = "INSUFFICIENT_COVERAGE"
    elif pos_count >= neg_count * 2 and pos_count >= 2:
        trend = "BULLISH_SHIFT"
    elif neg_count >= pos_count * 2 and neg_count >= 2:
        trend = "BEARISH_SHIFT"
    elif abs(pos_count - neg_count) <= 1 and (pos_count + neg_count) >= 3:
        trend = "VOLATILE"
    else:
        trend = "STABLE"

    return {
        "symbol": norm_sym,
        "timeframe": timeframe,
        "total_articles": total_articles,
        "average_sentiment_score": avg_score,
        "distribution": distribution,
        "sentiment_trend": trend,
        "is_insufficient_data": is_insufficient,
        "message": "Sufficient news coverage" if not is_insufficient else "Limited news coverage; sentiment score should be interpreted with caution.",
        "recent_articles": articles_out[:10],
    }


def get_sentiment_trends_timeline(
    db: Session,
    symbol: str,
    days: int = 14,
) -> List[Dict[str, Any]]:
    """
    Returns daily sentiment score aggregation timeline for charting.
    """
    norm_sym = normalize_symbol(symbol)
    cutoff = datetime.utcnow() - timedelta(days=days)

    records = (
        db.query(FinancialNews.published_at, NewsSentiment.sentiment_score, NewsSentiment.sentiment_label)
        .join(NewsSentiment, FinancialNews.id == NewsSentiment.news_id)
        .filter(
            (FinancialNews.symbol == norm_sym) | (NewsSentiment.symbol == norm_sym),
            FinancialNews.published_at >= cutoff,
        )
        .all()
    )

    daily_groups: Dict[str, List[Tuple[float, str]]] = {}
    for pub_at, score, label in records:
        d_str = pub_at.strftime("%Y-%m-%d")
        if d_str not in daily_groups:
            daily_groups[d_str] = []
        daily_groups[d_str].append((score, label))

    timeline = []
    for d_str in sorted(daily_groups.keys()):
        group = daily_groups[d_str]
        scores = [g[0] for g in group]
        pos = sum(1 for g in group if g[1] == "POSITIVE")
        neg = sum(1 for g in group if g[1] == "NEGATIVE")
        neu = sum(1 for g in group if g[1] == "NEUTRAL")
        mix = sum(1 for g in group if g[1] == "MIXED")

        timeline.append({
            "date": d_str,
            "avg_sentiment_score": round(float(np.mean(scores)), 2),
            "article_count": len(group),
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "mixed_count": mix,
        })

    return timeline


def analyze_news_price_correlation(
    db: Session,
    news_id: int,
) -> Dict[str, Any]:
    """
    Evaluates historical price and volume reaction around article publication timing without look-ahead bias.
    """
    news = db.query(FinancialNews).filter(FinancialNews.id == news_id).first()
    if not news or not news.symbol:
        return {"error": "Article or associated ticker symbol not found"}

    sym = news.symbol
    pub_dt = news.published_at
    pub_date_str = pub_dt.strftime("%Y-%m-%d")

    # Fetch 6-month historical OHLCV
    df, _, source = get_stock_history_df(sym, period="6mo")
    if df.empty or len(df) < 5:
        return {
            "symbol": sym,
            "news_id": news_id,
            "status": "UNAVAILABLE",
            "message": "Insufficient historical trading data to calculate correlation.",
        }

    # Compute technical indicators
    df_ind = compute_technical_indicators(df)
    df_ind = df_ind.sort_values("timestamp").reset_index(drop=True)

    # Find trading session index corresponding to or immediately following publication
    matching_indices = df_ind.index[df_ind["timestamp"] == pub_date_str].tolist()
    if matching_indices:
        target_idx = matching_indices[0]
    else:
        # Find closest subsequent trading date
        subsequent = df_ind.index[df_ind["timestamp"] >= pub_date_str].tolist()
        target_idx = subsequent[0] if subsequent else len(df_ind) - 1

    timing = news.market_session_timing or "MARKET_HOURS"
    session_row = df_ind.iloc[target_idx]
    prev_session = df_ind.iloc[target_idx - 1] if target_idx > 0 else session_row
    next_session = df_ind.iloc[target_idx + 1] if target_idx + 1 < len(df_ind) else session_row

    # Prices
    price_before = float(prev_session["close"])
    price_during = float(session_row["close"])
    price_after = float(next_session["close"])

    pct_session_change = round(((price_during - price_before) / price_before) * 100.0, 2) if price_before > 0 else 0.0
    pct_next_change = round(((price_after - price_during) / price_during) * 100.0, 2) if price_during > 0 else 0.0

    # Volume comparison
    curr_vol = int(session_row["volume"])
    # 20-day avg volume prior to target_idx
    slice_start = max(0, target_idx - 20)
    prior_vols = df_ind["volume"].iloc[slice_start:target_idx].dropna().tolist()
    avg_vol = float(np.mean(prior_vols)) if prior_vols else float(curr_vol)
    vol_ratio = round(curr_vol / avg_vol, 2) if avg_vol > 0 else 1.0

    # Indicator changes
    rsi_val = round(float(session_row["rsi_14"]), 2) if pd.notna(session_row.get("rsi_14")) else None
    macd_val = round(float(session_row["macd_histogram"]), 2) if pd.notna(session_row.get("macd_histogram")) else None

    # Check for Stage 5 Market Events around publication date
    events_found = (
        db.query(MarketEvent)
        .filter(MarketEvent.symbol == sym, MarketEvent.event_date == session_row["timestamp"])
        .all()
    )
    detected_events = [
        {"event_type": ev.event_type, "severity": ev.severity, "price_change_pct": ev.price_change_pct}
        for ev in events_found
    ]

    return {
        "news_id": news_id,
        "symbol": sym,
        "publication_timestamp": pub_dt.isoformat() + "Z",
        "market_session_timing": timing,
        "trading_session_date": str(session_row["timestamp"]),
        "price_metrics": {
            "price_before_publication": price_before,
            "session_close_price": price_during,
            "session_after_price": price_after,
            "session_change_pct": pct_session_change,
            "next_session_change_pct": pct_next_change,
        },
        "volume_metrics": {
            "session_volume": curr_vol,
            "volume_20d_average": round(avg_vol, 0),
            "volume_ratio": vol_ratio,
        },
        "technical_context": {
            "rsi_14": rsi_val,
            "macd_histogram": macd_val,
        },
        "detected_market_events": detected_events,
        "correlation_disclaimer": "Temporal proximity between news publication and price movement does not establish statistical causation. Other market and sector factors may have contributed.",
    }
