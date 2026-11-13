"""Intelligent Financial News Alerts Engine.

Module 6:
Monitors incoming news and sentiment shifts, evaluates user preferences, enforces
cooldown windows, and persists alerts to PostgreSQL with user isolation.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from backend.app.models.news import FinancialNews, NewsSentiment, NewsAlert
from backend.app.models.watchlist import WatchlistItem
from backend.app.models.alert import AlertPreferences
from backend.app.services.market_service import normalize_symbol


def evaluate_news_alerts_for_user(
    db: Session,
    user_id: int,
    cooldown_minutes: int = 60,
) -> List[NewsAlert]:
    """
    Evaluates recent un-alerted news against user preferences and watchlist.
    Enforces cooldown and deduplication.
    """
    now_utc = datetime.utcnow()
    cooldown_cutoff = now_utc - timedelta(minutes=cooldown_minutes)

    # 1. Fetch user watchlist symbols
    watchlist_items = db.query(WatchlistItem.symbol).filter(WatchlistItem.user_id == user_id).all()
    watchlist_symbols = {r[0] for r in watchlist_items}

    # 2. Query recent news (last 24 hours) with analyzed sentiments
    cutoff_24h = now_utc - timedelta(hours=24)
    news_rows = (
        db.query(FinancialNews, NewsSentiment)
        .join(NewsSentiment, FinancialNews.id == NewsSentiment.news_id)
        .filter(FinancialNews.published_at >= cutoff_24h)
        .order_by(FinancialNews.published_at.desc())
        .limit(30)
        .all()
    )

    # 3. Check existing alerts for user to enforce cooldown
    recent_alerts = (
        db.query(NewsAlert)
        .filter(NewsAlert.user_id == user_id, NewsAlert.created_at >= cooldown_cutoff)
        .all()
    )
    alerted_news_ids = {a.news_id for a in recent_alerts if a.news_id is not None}
    recent_alert_symbols = {a.symbol for a in recent_alerts if a.symbol is not None}

    triggered_alerts: List[NewsAlert] = []

    for fn, ns in news_rows:
        if fn.id in alerted_news_ids:
            continue

        sym = fn.symbol
        is_watchlist = sym in watchlist_symbols if sym else False
        score = ns.sentiment_score
        label = ns.sentiment_label
        title_lower = fn.title.lower()

        alert_type = None
        severity = "NORMAL"
        msg = ""

        # High Impact Negative
        if score <= -0.4 or any(w in title_lower for w in ["sebi penalty", "fraud", "raid", "insolvency", "default", "downgrade", "probe"]):
            alert_type = "HIGH_IMPACT_NEGATIVE"
            severity = "HIGH" if score > -0.7 else "CRITICAL"
            msg = f"Negative development detected: {fn.title} (Sentiment: {score:+.2f})."

        # Major Announcement
        elif fn.category in ["CORPORATE_ACTION", "BUSINESS_EXPANSION"] or any(w in title_lower for w in ["bonus", "dividend hike", "mega contract", "merger", "acquisition"]):
            alert_type = "MAJOR_ANNOUNCEMENT"
            severity = "NORMAL"
            msg = f"Corporate announcement: {fn.title} ({fn.category})."

        # Watchlist Breaking
        elif is_watchlist and (score >= 0.45 or score <= -0.35):
            alert_type = "WATCHLIST_BREAKING"
            severity = "NORMAL" if score > 0 else "HIGH"
            msg = f"News affecting watchlist stock {sym}: {fn.title} (Sentiment: {label})."

        # Significant Positive
        elif score >= 0.5:
            alert_type = "SIGNIFICANT_POSITIVE"
            severity = "NORMAL"
            msg = f"Positive catalyst: {fn.title} (Sentiment: {score:+.2f})."

        if alert_type:
            # Check symbol cooldown unless severity is CRITICAL
            if sym and sym in recent_alert_symbols and severity != "CRITICAL":
                continue

            alert_row = NewsAlert(
                user_id=user_id,
                news_id=fn.id,
                symbol=sym,
                alert_type=alert_type,
                severity=severity,
                title=f"[{severity}] {fn.company_name or sym or 'Market'}: {fn.title[:70]}...",
                message=msg,
                status="TRIGGERED",
                created_at=now_utc,
            )
            db.add(alert_row)
            triggered_alerts.append(alert_row)
            alerted_news_ids.add(fn.id)
            if sym:
                recent_alert_symbols.add(sym)

    if triggered_alerts:
        db.commit()
        for a in triggered_alerts:
            db.refresh(a)

    return triggered_alerts


def get_user_news_alerts(
    db: Session,
    user_id: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Retrieves news alerts for current user with user data isolation."""
    alerts = (
        db.query(NewsAlert)
        .filter(NewsAlert.user_id == user_id)
        .order_by(NewsAlert.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": a.id,
            "news_id": a.news_id,
            "symbol": a.symbol,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "title": a.title,
            "message": a.message,
            "status": a.status,
            "created_at": a.created_at.isoformat() + "Z" if a.created_at else None,
        }
        for a in alerts
    ]
