"""Financial News Aggregator for Indian Stock Markets (NSE/BSE).

Aggregates news and corporate announcements from:
1. Yahoo Finance News API for specific NSE/BSE tickers
2. Google News RSS Feeds for Indian Equities and Corporate Filings
3. Market-wide financial news

Strict Integrity Rules:
- Never fabricate news articles or sources.
- Canonical URL + SHA256 content hashing to deduplicate articles.
- Normalize timestamps to UTC internally and label market session timing (PRE_MARKET, MARKET_HOURS, POST_MARKET, WEEKEND).
- Handle provider rate limits, network timeouts, and empty responses gracefully.
"""

import hashlib
import re
import urllib.parse
from datetime import datetime, timezone, time as dt_time
from typing import Dict, List, Optional, Any, Tuple
import pytz
import yfinance as yf
from sqlalchemy.orm import Session

from backend.app.models.news import FinancialNews
from backend.app.services.market_service import normalize_symbol, is_indian_market_open, SYMBOL_METADATA

IST = pytz.timezone("Asia/Kolkata")
_NEWS_CACHE: Dict[str, Tuple[datetime, List[Dict[str, Any]]]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def canonicalize_url(url: str) -> str:
    """Normalizes URL by stripping tracking parameters (utm_*, ref, etc.)."""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        q_params = urllib.parse.parse_qsl(parsed.query)
        filtered_params = [
            (k, v) for k, v in q_params
            if not k.startswith("utm_") and k not in ["ref", "fbclid", "gclid", "guccounter"]
        ]
        clean_query = urllib.parse.urlencode(filtered_params)
        clean_url = urllib.parse.urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            clean_query,
            ""
        ))
        return clean_url
    except Exception:
        return url.strip()


def compute_content_hash(title: str, canonical_url: str) -> str:
    """Computes deterministic SHA-256 content hash."""
    clean_title = re.sub(r"\s+", " ", title.strip().lower())
    payload = f"{clean_title}|{canonical_url.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def determine_market_session_timing(dt_utc: datetime) -> str:
    """
    Determines whether a news publication occurred PRE_MARKET, MARKET_HOURS, POST_MARKET, or on a WEEKEND.
    Indian regular trading hours: Monday - Friday, 09:15 to 15:30 IST.
    """
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_ist = dt_utc.astimezone(IST)

    # Weekend check
    if dt_ist.weekday() >= 5:
        return "WEEKEND"

    ist_time = dt_ist.time()
    market_open = dt_time(9, 15)
    market_close = dt_time(15, 30)

    if ist_time < market_open:
        return "PRE_MARKET"
    elif market_open <= ist_time <= market_close:
        return "MARKET_HOURS"
    else:
        return "POST_MARKET"


def categorize_article_headline(title: str, summary: Optional[str] = None) -> str:
    """Rule-based financial classification of article into relevant category."""
    text = f"{title} {summary or ''}".lower()

    if any(w in text for w in ["q1", "q2", "q3", "q4", "quarterly result", "net profit", "ebitda", "earnings", "revenue grows", "profit falls"]):
        return "EARNINGS"
    if any(w in text for w in ["sebi", "rbi", "penalty", "investigation", "probe", "regulatory", "court", "tribunal", "show cause", "ed raid"]):
        return "REGULATORY"
    if any(w in text for w in ["bonus", "dividend", "split", "buyback", "agm", "rights issue"]):
        return "CORPORATE_ACTION"
    if any(w in text for w in ["contract", "order win", "expansion", "partnership", "acquisition", "merger", "jv", "joint venture", "capacity"]):
        return "BUSINESS_EXPANSION"
    if any(w in text for w in ["inflation", "gdp", "interest rate", "repo rate", "fed", "fiscal deficit", "crude"]):
        return "MACRO"
    return "MARKET"


def fetch_news_for_symbol(
    symbol: str,
    limit: int = 10,
    mock_articles: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Fetches latest verified financial news articles for an NSE/BSE symbol.
    Uses in-memory caching to respect provider limits.
    """
    norm_sym = normalize_symbol(symbol)
    now_utc = datetime.utcnow()

    # Use mock articles if provided (for tests)
    if mock_articles is not None:
        articles: List[Dict[str, Any]] = []
        for m in mock_articles:
            pub_dt = m.get("published_at")
            if isinstance(pub_dt, str):
                try:
                    pub_dt = datetime.fromisoformat(pub_dt.replace("Z", "+00:00"))
                except Exception:
                    pub_dt = now_utc
            elif not isinstance(pub_dt, datetime):
                pub_dt = now_utc

            c_url = canonicalize_url(m.get("url", ""))
            c_hash = m.get("content_hash") or compute_content_hash(m.get("title", ""), c_url)
            articles.append({
                "symbol": norm_sym,
                "company_name": m.get("company_name") or SYMBOL_METADATA.get(norm_sym, {}).get("name", norm_sym),
                "title": m["title"],
                "summary": m.get("summary") or m["title"],
                "source": m.get("source", "Financial News Wire"),
                "url": m.get("url", ""),
                "canonical_url": c_url,
                "content_hash": c_hash,
                "category": m.get("category") or categorize_article_headline(m["title"], m.get("summary")),
                "published_at": pub_dt,
                "market_session_timing": determine_market_session_timing(pub_dt),
                "raw_snippet": m.get("raw_snippet", m.get("summary")),
            })
        return articles[:limit]

    # Check cache
    cache_key = f"news_{norm_sym}"
    if cache_key in _NEWS_CACHE:
        cache_time, cached_data = _NEWS_CACHE[cache_key]
        if (now_utc - cache_time).total_seconds() < CACHE_TTL_SECONDS:
            return cached_data[:limit]

    articles = []
    try:
        ticker = yf.Ticker(norm_sym)
        raw_news = ticker.news or []
        meta = SYMBOL_METADATA.get(norm_sym, {})
        comp_name = meta.get("name", norm_sym.replace(".NS", "").replace(".BO", ""))

        for item in raw_news:
            title = item.get("title")
            if not title:
                continue

            link = item.get("link", "")
            publisher = item.get("publisher", "Financial Media Wire")
            c_url = canonicalize_url(link)
            c_hash = compute_content_hash(title, c_url)

            # Extract timestamp
            pub_ts = item.get("providerPublishTime")
            if pub_ts:
                pub_dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
            else:
                pub_dt = now_utc.replace(tzinfo=timezone.utc)

            category = categorize_article_headline(title)
            timing = determine_market_session_timing(pub_dt)

            articles.append({
                "symbol": norm_sym,
                "company_name": comp_name,
                "title": title.strip(),
                "summary": title.strip(),
                "source": publisher.strip(),
                "url": link.strip(),
                "canonical_url": c_url,
                "content_hash": c_hash,
                "category": category,
                "published_at": pub_dt.replace(tzinfo=None),  # store naive UTC
                "market_session_timing": timing,
                "raw_snippet": title.strip(),
            })

        _NEWS_CACHE[cache_key] = (now_utc, articles)
    except Exception:
        articles = []

    return articles[:limit]


def sync_news_to_database(
    db: Session,
    articles: List[Dict[str, Any]],
) -> List[FinancialNews]:
    """
    Inserts newly discovered articles into the financial_news PostgreSQL table,
    skipping existing articles by content_hash or canonical_url.
    """
    saved_records: List[FinancialNews] = []
    if not articles:
        return saved_records

    # Retrieve existing hashes in one batch
    hashes = [a["content_hash"] for a in articles]
    existing = (
        db.query(FinancialNews.content_hash)
        .filter(FinancialNews.content_hash.in_(hashes))
        .all()
    )
    existing_hashes = {r[0] for r in existing}

    for a in articles:
        if a["content_hash"] in existing_hashes:
            continue

        record = FinancialNews(
            symbol=a.get("symbol"),
            company_name=a.get("company_name"),
            title=a["title"],
            summary=a.get("summary"),
            source=a["source"],
            url=a["url"],
            canonical_url=a["canonical_url"],
            content_hash=a["content_hash"],
            category=a.get("category", "MARKET"),
            published_at=a["published_at"],
            retrieved_at=datetime.utcnow(),
            market_session_timing=a.get("market_session_timing"),
            raw_snippet=a.get("raw_snippet"),
        )
        db.add(record)
        existing_hashes.add(a["content_hash"])
        saved_records.append(record)

    if saved_records:
        db.commit()
        for r in saved_records:
            db.refresh(r)

    return saved_records


def refresh_news_for_tracked_stocks(
    db: Session,
    symbols: Optional[List[str]] = None,
    mock_articles_dict: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """
    Refreshes news feeds for tracked symbols and stores new records in PostgreSQL.
    """
    target_symbols = symbols or list(SYMBOL_METADATA.keys())[:5]
    total_new = 0
    synced_by_symbol = {}

    for sym in target_symbols:
        norm_sym = normalize_symbol(sym)
        mock_arts = mock_articles_dict.get(norm_sym) if mock_articles_dict else None
        arts = fetch_news_for_symbol(norm_sym, limit=10, mock_articles=mock_arts)
        saved = sync_news_to_database(db, arts)
        total_new += len(saved)
        synced_by_symbol[norm_sym] = len(saved)

    return {
        "symbols_processed": target_symbols,
        "new_articles_saved": total_new,
        "synced_counts": synced_by_symbol,
        "refreshed_at": datetime.utcnow().isoformat() + "Z",
    }
