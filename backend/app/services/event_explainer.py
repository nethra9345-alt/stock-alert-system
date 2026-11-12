import datetime
from typing import List, Dict, Any, Optional
import yfinance as yf


def parse_yfinance_news_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extracts standardized news attributes from yfinance news item."""
    if not isinstance(item, dict):
        return None

    # Handle modern yfinance v0.2.40+ content wrapper
    content = item.get("content", item)
    if not isinstance(content, dict):
        content = item

    title = content.get("title") or item.get("title")
    if not title:
        return None

    # Extract publisher
    publisher = None
    prov = content.get("provider") or item.get("publisher")
    if isinstance(prov, dict):
        publisher = prov.get("displayName") or prov.get("name")
    elif isinstance(prov, str):
        publisher = prov

    # Extract URL
    url = None
    canon = content.get("canonicalUrl") or content.get("clickThroughUrl") or item.get("link")
    if isinstance(canon, dict):
        url = canon.get("url")
    elif isinstance(canon, str):
        url = canon

    # Extract pubDate (ISO string or unix timestamp)
    pub_date_str = content.get("pubDate") or item.get("pubDate")
    pub_time = item.get("providerPublishTime")

    parsed_date = None
    if pub_date_str and isinstance(pub_date_str, str):
        try:
            # Handles e.g. "2026-11-03T07:04:25Z"
            parsed_date = datetime.datetime.fromisoformat(pub_date_str.replace("Z", "+00:00")).date()
        except Exception:
            pass
    elif pub_time and isinstance(pub_time, (int, float)):
        try:
            parsed_date = datetime.datetime.fromtimestamp(pub_time, datetime.timezone.utc).date()
            pub_date_str = parsed_date.strftime("%Y-%m-%d")
        except Exception:
            pass

    return {
        "title": title.strip(),
        "url": url,
        "publisher": publisher or "Market Wire",
        "published_at": pub_date_str or (parsed_date.strftime("%Y-%m-%d") if parsed_date else None),
        "date_obj": parsed_date
    }


def fetch_relevant_news(symbol: str, target_date_str: str, window_days: int = 4) -> List[Dict[str, Any]]:
    """
    Fetches genuine news articles from yfinance and filters for those published within
    the target date window (+/- window_days).
    """
    try:
        target_date = datetime.date.fromisoformat(target_date_str)
    except Exception:
        return []

    try:
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news or []
    except Exception:
        return []

    matched_sources: List[Dict[str, Any]] = []

    for item in raw_news:
        parsed = parse_yfinance_news_item(item)
        if not parsed:
            continue

        item_date = parsed.get("date_obj")
        if item_date:
            delta_days = abs((item_date - target_date).days)
            if delta_days <= window_days:
                matched_sources.append({
                    "title": parsed["title"],
                    "url": parsed["url"],
                    "publisher": parsed["publisher"],
                    "published_at": parsed["published_at"]
                })
        else:
            # If no date could be parsed, do not assume relevance
            continue

    return matched_sources


def generate_event_explanation(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates an objective, verified explanation for a detected market event.
    Distinguishes confirmed announcements from unverified technical movements.
    """
    symbol = event["symbol"]
    event_date = event["event_date"]
    event_type = event["event_type"].replace("_", " ").title()
    pct = event["price_change_pct"]
    vol_ratio = event["volume_ratio"]
    curr_close = event["close_price"]

    # Retrieve verified news published around event date
    sources = fetch_relevant_news(symbol, event_date, window_days=4)

    is_verified = len(sources) > 0

    # Format factual movement summary
    direction = "gained" if pct > 0 else "declined"
    pct_formatted = f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"

    summary = (
        f"{symbol} experienced a {pct_formatted} {event_type} on {event_date}, "
        f"closing at ₹{curr_close:,.2f} with a {vol_ratio:.1f}x volume anomaly."
    )

    if is_verified:
        top_headlines = [s["title"] for s in sources[:2]]
        headline_text = " | ".join(top_headlines)
        detail = (
            f"Verified market catalyst detected: {headline_text}. "
            f"The movement was supported by elevated trading activity ({vol_ratio:.1f}x of 20-day average volume)."
        )
    else:
        detail = (
            f"No verified corporate disclosure or news release was found within the trading window. "
            f"This {event_type} may have been driven by broader benchmark index momentum, sector reallocation, "
            f"or institutional block positioning."
        )

    return {
        "explanation_summary": summary,
        "explanation_detail": detail,
        "sources": sources,
        "is_verified": is_verified
    }
