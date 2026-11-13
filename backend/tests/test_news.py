"""Deterministic Tests for Stage 8: Financial News Intelligence & Market Sentiment Analysis."""

import pytest
from datetime import datetime, timezone, timedelta
import pytz
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.watchlist import WatchlistItem
from backend.app.models.news import FinancialNews, NewsSentiment, CompanySentimentDaily, NewsAlert
from backend.app.services.news_aggregator import (
    canonicalize_url,
    compute_content_hash,
    determine_market_session_timing,
    categorize_article_headline,
    fetch_news_for_symbol,
    sync_news_to_database,
)
from backend.app.services.news_sentiment import (
    calculate_rule_based_sentiment,
    extract_companies_mentioned,
    extract_financial_figures,
    analyze_article_content,
    analyze_and_persist_news_sentiment,
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

client = TestClient(app)
IST = pytz.timezone("Asia/Kolkata")


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session: Session):
    user = db_session.query(User).filter(User.email == "news_analyst@stockpulse.ai").first()
    if not user:
        user = User(
            email="news_analyst@stockpulse.ai",
            username="news_analyst",
            full_name="News Sentiment Analyst",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def test_news_url_canonicalization_and_deduplication(db_session: Session):
    """Verify stripping tracking query params and deterministic hash generation."""
    url1 = "https://www.reuters.com/business/reliance-q3-results?utm_source=twitter&utm_medium=social&ref=feed"
    url2 = "https://www.reuters.com/business/reliance-q3-results"

    c_url1 = canonicalize_url(url1)
    c_url2 = canonicalize_url(url2)
    assert c_url1 == c_url2
    assert "utm_source" not in c_url1

    hash1 = compute_content_hash("Reliance Q3 profit jumps 15%", c_url1)
    hash2 = compute_content_hash("  reliance q3 profit jumps 15%  ", c_url2)
    assert hash1 == hash2

    # Clean prior test news
    db_session.query(FinancialNews).filter(FinancialNews.content_hash == hash1).delete()
    db_session.commit()

    # Sync batch with duplicates
    mock_batch = [
        {
            "symbol": "RELIANCE.NS",
            "company_name": "Reliance Industries",
            "title": "Reliance Q3 profit jumps 15%",
            "source": "Reuters",
            "url": url1,
            "canonical_url": c_url1,
            "content_hash": hash1,
            "published_at": datetime.utcnow(),
            "category": "EARNINGS",
        },
        {
            "symbol": "RELIANCE.NS",
            "company_name": "Reliance Industries",
            "title": "Reliance Q3 profit jumps 15%",
            "source": "Reuters",
            "url": url2,
            "canonical_url": c_url2,
            "content_hash": hash1,
            "published_at": datetime.utcnow(),
            "category": "EARNINGS",
        },
    ]

    saved = sync_news_to_database(db_session, mock_batch)
    assert len(saved) == 1  # Second duplicate ignored


def test_market_session_timing_classification():
    """Verify classification of news into PRE_MARKET, MARKET_HOURS, POST_MARKET, and WEEKEND."""
    # 1. Friday 08:30 IST -> PRE_MARKET (03:00 UTC)
    fri_pre = datetime(2026, 6, 12, 3, 0, 0, tzinfo=timezone.utc)
    assert determine_market_session_timing(fri_pre) == "PRE_MARKET"

    # 2. Friday 11:30 IST -> MARKET_HOURS (06:00 UTC)
    fri_during = datetime(2026, 6, 12, 6, 0, 0, tzinfo=timezone.utc)
    assert determine_market_session_timing(fri_during) == "MARKET_HOURS"

    # 3. Friday 16:30 IST -> POST_MARKET (11:00 UTC)
    fri_post = datetime(2026, 6, 12, 11, 0, 0, tzinfo=timezone.utc)
    assert determine_market_session_timing(fri_post) == "POST_MARKET"

    # 4. Saturday 12:00 IST -> WEEKEND
    sat_weekend = datetime(2026, 6, 13, 6, 30, 0, tzinfo=timezone.utc)
    assert determine_market_session_timing(sat_weekend) == "WEEKEND"


def test_sentiment_classification_positive():
    """Verify detection of positive financial catalysts and growth signals."""
    headline = "Reliance Industries net profit surges 28% on strong quarterly revenue, dividend declared"
    sent = calculate_rule_based_sentiment(headline)
    assert sent["sentiment_label"] == "POSITIVE"
    assert sent["sentiment_score"] > 0.2
    assert sent["confidence"] >= 0.70


def test_sentiment_classification_negative():
    """Verify detection of negative catalysts, regulatory action, and profit declines."""
    headline = "SEBI issues show cause notice and penalty to firm following fraud probe as net profit slumps 35%"
    sent = calculate_rule_based_sentiment(headline)
    assert sent["sentiment_label"] == "NEGATIVE"
    assert sent["sentiment_score"] < -0.2
    assert sent["confidence"] >= 0.70


def test_sentiment_classification_neutral():
    """Verify neutral classification for routine operational/calendar news."""
    headline = "Board meeting of Tata Consultancy Services scheduled on October 15 to consider quarterly accounts"
    sent = calculate_rule_based_sentiment(headline)
    assert sent["sentiment_label"] == "NEUTRAL"
    assert sent["sentiment_score"] == 0.0


def test_sentiment_classification_mixed():
    """Verify mixed classification when opposing operational forces collide."""
    headline = "Infosys reports revenue growth of 18% but net profit declines on rising operational costs"
    sent = calculate_rule_based_sentiment(headline)
    assert sent["sentiment_label"] == "MIXED"


def test_entity_and_financial_figures_extraction():
    """Verify entity recognition for symbols and extraction of rupee/percentage figures."""
    text = "Tata Consultancy Services secures mega contract worth ₹12,500 Cr as operating margins rise by 4.5%."
    entities = extract_companies_mentioned(text)
    assert "TCS.NS" in entities

    figures = extract_financial_figures(text)
    assert any("12,500" in f for f in figures)
    assert any("4.5%" in f for f in figures)


def test_company_sentiment_tracking_and_sample_size_flag(db_session: Session):
    """Verify sentiment distribution aggregation and sample size warning."""
    import uuid
    u = uuid.uuid4().hex[:6].upper()
    test_sym = f"INFY_{u}.NS"
    now = datetime.utcnow()

    # Seed 1 single article (insufficient sample size test)
    fn1 = FinancialNews(
        symbol=test_sym,
        company_name="Infosys Ltd",
        title="Infosys announces fresh partnership with global cloud provider",
        source="Tech Wire",
        url=f"https://techwire.in/infy1_{u}",
        canonical_url=f"https://techwire.in/infy1_{u}",
        content_hash=f"infy_hash_1_{u}",
        category="BUSINESS_EXPANSION",
        published_at=now - timedelta(hours=2),
    )
    db_session.add(fn1)
    db_session.commit()
    db_session.refresh(fn1)

    ns1 = NewsSentiment(
        news_id=fn1.id,
        symbol=test_sym,
        sentiment_label="POSITIVE",
        sentiment_score=0.6,
        confidence=0.8,
    )
    db_session.add(ns1)
    db_session.commit()

    summary1 = calculate_company_sentiment_summary(db_session, test_sym, timeframe="7d")
    assert summary1["total_articles"] == 1
    assert summary1["is_insufficient_data"] is True
    assert summary1["sentiment_trend"] == "INSUFFICIENT_COVERAGE"

    # Seed 2 more positive articles
    for i in range(2, 4):
        fn = FinancialNews(
            symbol=test_sym,
            company_name="Infosys Ltd",
            title=f"Infosys net profit surges in Q{i} expansion",
            source="Financial Wire",
            url=f"https://finwire.in/infy{i}_{u}",
            canonical_url=f"https://finwire.in/infy{i}_{u}",
            content_hash=f"infy_hash_{i}_{u}",
            category="EARNINGS",
            published_at=now - timedelta(hours=i * 2),
        )
        db_session.add(fn)
        db_session.commit()
        db_session.refresh(fn)

        ns = NewsSentiment(
            news_id=fn.id,
            symbol=test_sym,
            sentiment_label="POSITIVE",
            sentiment_score=0.7,
            confidence=0.85,
        )
        db_session.add(ns)
    db_session.commit()

    summary2 = calculate_company_sentiment_summary(db_session, test_sym, timeframe="7d")
    assert summary2["total_articles"] == 3
    assert summary2["is_insufficient_data"] is False
    assert summary2["sentiment_trend"] == "BULLISH_SHIFT"
    assert summary2["distribution"]["positive"] == 3


def test_news_price_correlation(db_session: Session):
    """Verify temporal price alignment and disclaimer presence without look-ahead bias."""
    import uuid
    u = uuid.uuid4().hex[:6]
    fn = FinancialNews(
        symbol="RELIANCE.NS",
        company_name="Reliance Industries",
        title="Reliance enters green energy agreement with global consortium",
        source="Economic Times",
        url=f"https://economictimes.indiatimes.com/reliance-green_{u}",
        canonical_url=f"https://economictimes.indiatimes.com/reliance-green_{u}",
        content_hash=f"reliance_green_hash_{u}",
        category="BUSINESS_EXPANSION",
        published_at=datetime.utcnow() - timedelta(days=2),
        market_session_timing="MARKET_HOURS",
    )
    db_session.add(fn)
    db_session.commit()
    db_session.refresh(fn)

    res = analyze_news_price_correlation(db_session, fn.id)
    assert res["symbol"] == "RELIANCE.NS"
    assert "price_metrics" in res
    assert "volume_metrics" in res
    assert "correlation_disclaimer" in res
    assert "does not establish statistical causation" in res["correlation_disclaimer"]


def test_intelligent_news_alerts_and_cooldown(db_session: Session, test_user: User):
    """Verify alert generation for negative/breaking news and cooldown enforcement."""
    import uuid
    u = uuid.uuid4().hex[:6]
    # Ensure test user watches RELIANCE.NS
    wl = (
        db_session.query(WatchlistItem)
        .filter(WatchlistItem.user_id == test_user.id, WatchlistItem.symbol == "RELIANCE.NS")
        .first()
    )
    if not wl:
        wl = WatchlistItem(user_id=test_user.id, symbol="RELIANCE.NS", company_name="Reliance Industries")
        db_session.add(wl)
        db_session.commit()

    # Clear prior alerts for test user
    db_session.query(NewsAlert).filter(NewsAlert.user_id == test_user.id).delete()
    db_session.commit()

    now = datetime.utcnow()
    # Seed a high-impact negative article
    fn = FinancialNews(
        symbol="RELIANCE.NS",
        company_name="Reliance Industries",
        title="SEBI issues penalty to subsidiary over disclosure compliance",
        source="Financial Express",
        url=f"https://financialexpress.com/sebi-penalty-test_{u}",
        canonical_url=f"https://financialexpress.com/sebi-penalty-test_{u}",
        content_hash=f"sebi_penalty_hash_test_{u}",
        category="REGULATORY",
        published_at=now - timedelta(minutes=10),
    )
    db_session.add(fn)
    db_session.commit()
    db_session.refresh(fn)

    ns = NewsSentiment(
        news_id=fn.id,
        symbol="RELIANCE.NS",
        sentiment_label="NEGATIVE",
        sentiment_score=-0.65,
        confidence=0.9,
    )
    db_session.add(ns)
    db_session.commit()

    alerts_triggered = evaluate_news_alerts_for_user(db_session, test_user.id, cooldown_minutes=60)
    assert len(alerts_triggered) >= 1
    first_alert = alerts_triggered[0]
    assert first_alert.symbol == "RELIANCE.NS"
    assert first_alert.severity in ["HIGH", "CRITICAL"]

    # Re-evaluating immediately should not create duplicate alerts within cooldown
    dup_eval = evaluate_news_alerts_for_user(db_session, test_user.id, cooldown_minutes=60)
    assert len(dup_eval) == 0


def test_news_api_endpoints_integration(db_session: Session):
    """Verify FastAPI news endpoints via TestClient."""
    # 1. Market overview
    resp = client.get("/api/news/market/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_sentiment" in data
    assert "distribution" in data

    # 2. List news
    resp = client.get("/api/news?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data

    # 3. Company sentiment summary
    resp = client.get("/api/news/sentiment/RELIANCE.NS?timeframe=7d")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "RELIANCE.NS"
    assert "distribution" in data

    # 4. Sentiment trends timeline
    resp = client.get("/api/news/sentiment/trends/RELIANCE.NS?days=14")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

    # 5. News alerts endpoint
    resp = client.get("/api/news/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
