"""RAG Knowledge Retrieval Layer for StockPulse AI.

Aggregates multi-source financial intelligence:
- Real-time/EOD market quotes & historical prices
- Audited financial statements, ratios, and fundamentals
- Rule-based algorithmic technical indicators
- Historical market anomaly events from PostgreSQL
- External news headlines (sanitized with prompt injection defenses)
- User portfolio holdings (strictly opt-in with explicit authorization)
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import yfinance as yf

from backend.app.services.market_service import normalize_symbol, get_stock_quote
from backend.app.services.fundamentals import get_company_fundamentals
from backend.app.services.technical_analysis import analyze_technical_structure
from backend.app.models.event import MarketEvent
from backend.app.models.portfolio import PortfolioTransaction
from backend.app.models.news import FinancialNews, NewsSentiment
from backend.app.services.portfolio_analytics import compute_fifo_portfolio_holdings

# Prompt injection patterns to detect and strip from untrusted web/user text
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"(?i)system\s*prompt",
    r"(?i)you\s+are\s+now\s+(an?\s+)?unrestricted",
    r"(?i)dan\s+mode",
    r"(?i)disregard\s+(all\s+)?(rules|safety|guardrails)",
    r"(?i)bypass\s+(all\s+)?filters?",
    r"(?i)reveal\s+(your\s+)?instructions?",
    r"(?i)roleplay\s+as",
    r"(?i)as\s+an\s+ai\s+without\s+limitations?",
]


def sanitize_untrusted_text(text: Optional[str], max_chars: int = 800) -> str:
    """Sanitizes untrusted text from news feeds or user prompts against prompt injection."""
    if not text:
        return ""
    clean = str(text).strip()
    for pat in INJECTION_PATTERNS:
        clean = re.sub(pat, "[FILTERED_INSTRUCTION]", clean)
    # Remove control characters
    clean = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", clean)
    if len(clean) > max_chars:
        clean = clean[:max_chars] + "... [TRUNCATED]"
    return clean


def retrieve_rag_context(
    symbol: str,
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
    include_portfolio: bool = False,
    mock_fundamentals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Assembles a comprehensive, verifiable RAG intelligence dossier for a stock.

    Args:
        symbol: Ticker symbol (e.g. 'RELIANCE.NS')
        db: SQLAlchemy database session (for events & portfolio)
        user_id: Authenticated user ID
        include_portfolio: Explicit authorization to include user's portfolio holding data
        mock_fundamentals: Optional mock data for test environments
    """
    norm_sym = normalize_symbol(symbol)
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    citations: List[Dict[str, str]] = []

    # 1. Market Quote & Metadata
    try:
        quote = get_stock_quote(norm_sym)
        quote_dict = {
            "symbol": quote.symbol,
            "name": quote.name,
            "price": quote.price,
            "change": quote.change,
            "change_percent": quote.change_percent,
            "open": quote.open,
            "high": quote.high,
            "low": quote.low,
            "previous_close": quote.previous_close,
            "exchange": quote.exchange,
            "sector": quote.sector,
            "is_market_open": quote.is_market_open,
            "timestamp": quote.timestamp,
        }
        citations.append({
            "source": f"NSE/BSE Market Data ({quote.exchange})",
            "category": "Market Quote",
            "timestamp": quote.timestamp,
            "details": f"Price ₹{quote.price:,.2f} ({quote.change_percent:+.2f}%)",
        })
    except Exception as e:
        quote_dict = {"symbol": norm_sym, "status": "UNAVAILABLE", "error": str(e)}

    # 2. Company Fundamentals
    try:
        fundamentals = get_company_fundamentals(norm_sym, mock_data=mock_fundamentals)
        citations.append({
            "source": "Audited Company Financials & Filings",
            "category": "Fundamentals",
            "timestamp": fundamentals.get("retrieved_at", now_str),
            "details": f"PE: {fundamentals.get('valuation', {}).get('pe_trailing', 'N/A')}x, Rev Growth: {fundamentals.get('growth', {}).get('revenue_growth_yoy_pct', 'N/A')}%",
        })
    except Exception as e:
        fundamentals = {"symbol": norm_sym, "status": "UNAVAILABLE", "error": str(e)}

    # 3. Technical Analysis
    try:
        technicals = analyze_technical_structure(norm_sym, period="6mo")
        citations.append({
            "source": "StockPulse Technical Indicator Synthesis Engine",
            "category": "Technical Analysis",
            "timestamp": technicals.get("retrieved_at", now_str),
            "details": f"Posture: {technicals.get('overall_sentiment', 'NEUTRAL')}, RSI: {technicals.get('indicators', {}).get('rsi_14', 'N/A')}",
        })
    except Exception as e:
        technicals = {"symbol": norm_sym, "status": "UNAVAILABLE", "error": str(e)}

    # 4. Market Events Intelligence (from PostgreSQL)
    market_events: List[Dict[str, Any]] = []
    if db is not None:
        try:
            evs = (
                db.query(MarketEvent)
                .filter(MarketEvent.symbol == norm_sym)
                .order_by(MarketEvent.event_date.desc())
                .limit(5)
                .all()
            )
            for ev in evs:
                market_events.append({
                    "date": ev.event_date,
                    "event_type": ev.event_type,
                    "severity": ev.severity,
                    "price_change_pct": ev.price_change_pct,
                    "volume_ratio": ev.volume_ratio,
                    "explanation": ev.explanation_summary,
                })
            if market_events:
                citations.append({
                    "source": "StockPulse Market Event Intelligence DB",
                    "category": "Market Events",
                    "timestamp": now_str,
                    "details": f"{len(market_events)} historical anomaly events detected",
                })
        except Exception:
            pass

    # 5. Verified Market News & Sentiment Intelligence
    news_items: List[Dict[str, str]] = []
    if db is not None:
        try:
            db_news = (
                db.query(FinancialNews, NewsSentiment)
                .outerjoin(NewsSentiment, FinancialNews.id == NewsSentiment.news_id)
                .filter(FinancialNews.symbol == norm_sym)
                .order_by(FinancialNews.published_at.desc())
                .limit(5)
                .all()
            )
            for fn, ns in db_news:
                title = sanitize_untrusted_text(fn.title)
                publisher = sanitize_untrusted_text(fn.source, max_chars=100)
                sent_label = ns.sentiment_label if ns else "NEUTRAL"
                sent_score = f"{ns.sentiment_score:+.2f}" if ns else "0.00"
                news_items.append({
                    "title": title,
                    "publisher": publisher,
                    "link": fn.url,
                    "sentiment_label": sent_label,
                    "sentiment_score": sent_score,
                    "published_at": fn.published_at.strftime("%Y-%m-%d %H:%M UTC") if fn.published_at else "",
                })
            if news_items:
                citations.append({
                    "source": "StockPulse News Intelligence & Sentiment Database",
                    "category": "News Sentiment",
                    "timestamp": now_str,
                    "details": f"{len(news_items)} verified articles with AI sentiment",
                })
        except Exception:
            pass

    if not news_items and not mock_fundamentals:
        try:
            ticker = yf.Ticker(norm_sym)
            raw_news = ticker.news or []
            for item in raw_news[:4]:
                title = sanitize_untrusted_text(item.get("title", ""))
                publisher = sanitize_untrusted_text(item.get("publisher", "Financial Media"), max_chars=100)
                link = item.get("link", "")
                if title:
                    news_items.append({
                        "title": title,
                        "publisher": publisher,
                        "link": link,
                    })
            if news_items:
                citations.append({
                    "source": "Financial Media & News Wire",
                    "category": "News",
                    "timestamp": now_str,
                    "details": f"{len(news_items)} recent news headlines",
                })
        except Exception:
            pass

    # 6. Portfolio Holding (Strictly Opt-in & Authorized)
    portfolio_context: Optional[Dict[str, Any]] = None
    if include_portfolio and db is not None and user_id is not None:
        try:
            user_txs = (
                db.query(PortfolioTransaction)
                .filter(PortfolioTransaction.user_id == user_id)
                .all()
            )
            holdings_summary = compute_fifo_portfolio_holdings(user_txs)
            matching_holding = next(
                (h for h in holdings_summary.get("holdings", []) if h["symbol"] == norm_sym),
                None
            )
            if matching_holding:
                qty = matching_holding.get("total_quantity", matching_holding.get("quantity", 0.0))
                unrealized_pct = matching_holding.get("unrealized_pnl_percent", matching_holding.get("unrealized_pnl_pct", 0.0))
                alloc_pct = matching_holding.get("portfolio_weight_pct", matching_holding.get("portfolio_allocation_pct", 0.0))
                portfolio_context = {
                    "shares_held": qty,
                    "avg_buy_price": matching_holding.get("avg_buy_price", 0.0),
                    "invested_value": matching_holding.get("invested_value", 0.0),
                    "current_value": matching_holding.get("current_value", 0.0),
                    "unrealized_pnl": matching_holding.get("unrealized_pnl", 0.0),
                    "unrealized_pnl_pct": unrealized_pct,
                    "portfolio_allocation_pct": alloc_pct,
                }
                citations.append({
                    "source": "User Portfolio Database (Authorized Private Data)",
                    "category": "Portfolio Holding",
                    "timestamp": now_str,
                    "details": f"Holding {qty} shares @ ₹{matching_holding.get('avg_buy_price', 0.0):,.2f}",
                })
            else:
                portfolio_context = {"shares_held": 0, "status": "NO_POSITION"}
        except Exception:
            portfolio_context = {"error": "Failed to read portfolio securely"}

    # Build Prompt-Ready Context Markdown String
    lines: List[str] = []
    lines.append(f"### FINANCIAL INTELLIGENCE CONTEXT FOR {norm_sym}")
    lines.append(f"Timestamp: {now_str}\n")

    # Quote
    lines.append("#### 1. Real-Time / EOD Market Quote [Source: NSE/BSE Market Data]")
    lines.append(f"- Company: {quote_dict.get('name', norm_sym)} ({quote_dict.get('exchange', 'NSE')})")
    lines.append(f"- Sector: {quote_dict.get('sector', 'Equities')}")
    lines.append(f"- Current Price: ₹{quote_dict.get('price', 'UNAVAILABLE')} ({quote_dict.get('change_percent', 0):+.2f}%)")
    lines.append(f"- Previous Close: ₹{quote_dict.get('previous_close', 'UNAVAILABLE')}")
    lines.append(f"- Day Range: Low ₹{quote_dict.get('low', 'N/A')} - High ₹{quote_dict.get('high', 'N/A')}\n")

    # Fundamentals
    lines.append("#### 2. Company Fundamentals & Valuation [Source: Audited Financials]")
    val = fundamentals.get("valuation", {})
    gro = fundamentals.get("growth", {})
    pro = fundamentals.get("profitability", {})
    fin = fundamentals.get("financial_health", {})
    div = fundamentals.get("dividends", {})

    lines.append(f"- Market Cap: ₹{val.get('market_cap_formatted', 'UNAVAILABLE')}")
    lines.append(f"- Trailing P/E: {val.get('pe_trailing', 'UNAVAILABLE')}x | Forward P/E: {val.get('pe_forward', 'UNAVAILABLE')}x")
    lines.append(f"- Price-to-Book (P/B): {val.get('price_to_book', 'UNAVAILABLE')}x | Price-to-Sales: {val.get('price_to_sales', 'UNAVAILABLE')}x")
    lines.append(f"- EV/EBITDA: {val.get('ev_to_ebitda', 'UNAVAILABLE')}x")
    lines.append(f"- Revenue Growth (YoY): {gro.get('revenue_growth_yoy_pct', 'UNAVAILABLE')}%")
    lines.append(f"- Profit Growth (YoY): {gro.get('profit_growth_yoy_pct', 'UNAVAILABLE')}%")
    lines.append(f"- Return on Equity (ROE): {pro.get('return_on_equity_pct', 'UNAVAILABLE')}%")
    lines.append(f"- ROCE: {pro.get('roce_pct', 'UNAVAILABLE')}%")
    lines.append(f"- Operating Margin: {pro.get('operating_margin_pct', 'UNAVAILABLE')}% | Net Margin: {pro.get('net_margin_pct', 'UNAVAILABLE')}%")
    lines.append(f"- Debt-to-Equity: {fin.get('debt_to_equity', 'UNAVAILABLE')}x | Current Ratio: {fin.get('current_ratio', 'UNAVAILABLE')}x")
    lines.append(f"- Dividend Yield: {div.get('dividend_yield_pct', 'UNAVAILABLE')}%")
    if fundamentals.get("missing_metrics"):
        lines.append(f"- Note: The following metrics were unavailable from regulatory filings: {', '.join(fundamentals['missing_metrics'])}")
    lines.append("")

    # Technicals
    lines.append("#### 3. Technical Posture & Momentum [Source: Technical Indicator Synthesis]")
    lines.append(f"- Overall Technical Posture: {technicals.get('overall_sentiment', 'NEUTRAL')}")
    ind = technicals.get("indicators", {})
    lines.append(f"- Moving Averages: SMA 20: ₹{ind.get('sma_20', 'N/A')}, SMA 50: ₹{ind.get('sma_50', 'N/A')}, SMA 200: ₹{ind.get('sma_200', 'N/A')}")
    lines.append(f"- Wilder RSI (14): {ind.get('rsi_14', 'N/A')}")
    lines.append(f"- MACD Line: {ind.get('macd_line', 'N/A')} | Signal: {ind.get('macd_signal', 'N/A')} | Hist: {ind.get('macd_histogram', 'N/A')}")
    lines.append(f"- Historical Volatility (20-day Annualized): {ind.get('historical_volatility_20d_annualized', 'N/A')}%")
    sup = technicals.get("support_levels", {})
    res = technicals.get("resistance_levels", {})
    lines.append(f"- Key Support Levels: Pivot ₹{sup.get('pivot', 'N/A')}, S1 ₹{sup.get('s1', 'N/A')}, 20-Day Low ₹{sup.get('swing_low_20d', 'N/A')}")
    lines.append(f"- Key Resistance Levels: Pivot ₹{res.get('pivot', 'N/A')}, R1 ₹{res.get('r1', 'N/A')}, 20-Day High ₹{res.get('swing_high_20d', 'N/A')}")
    if technicals.get("bullish_signals"):
        lines.append(f"- Bullish Signals: {'; '.join(technicals['bullish_signals'])}")
    if technicals.get("bearish_signals"):
        lines.append(f"- Bearish Signals: {'; '.join(technicals['bearish_signals'])}")
    if technicals.get("neutral_conflicts"):
        lines.append(f"- Neutral/Conflicting Signals: {'; '.join(technicals['neutral_conflicts'])}")
    lines.append("")

    # Events
    if market_events:
        lines.append("#### 4. Historical Market Events & Anomalies [Source: Market Events Database]")
        for ev in market_events:
            lines.append(f"- {ev['date']} | {ev['event_type']} ({ev['severity']}): Price {ev['price_change_pct']:+.2f}%, Volume {ev['volume_ratio']}x. {ev.get('explanation', '')}")
        lines.append("")

    # News
    if news_items:
        lines.append("#### 5. Recent Verified News Headlines [Source: Financial News Intelligence]")
        for n in news_items:
            sent_str = f" [Sentiment: {n['sentiment_label']}]" if "sentiment_label" in n else ""
            lines.append(f"- [{n['publisher']}] {n['title']}{sent_str}")
        lines.append("")

    # Portfolio
    if portfolio_context is not None:
        lines.append("#### 6. User Portfolio Holding (Private Authorized) [Source: Portfolio DB]")
        if portfolio_context.get("shares_held", 0) > 0:
            lines.append(f"- Position: {portfolio_context['shares_held']} shares held")
            lines.append(f"- Average Buy Price: ₹{portfolio_context['avg_buy_price']:,.2f}")
            lines.append(f"- Invested Value: ₹{portfolio_context['invested_value']:,.2f} | Current Value: ₹{portfolio_context['current_value']:,.2f}")
            lines.append(f"- Unrealized P&L: ₹{portfolio_context['unrealized_pnl']:+,.2f} ({portfolio_context['unrealized_pnl_pct']:+.2f}%)")
            lines.append(f"- Portfolio Weight: {portfolio_context['portfolio_allocation_pct']:.2f}%")
        else:
            lines.append("- Position: The user currently has 0 open shares of this stock in their tracked portfolio.")
        lines.append("")

    prompt_context_text = "\n".join(lines)

    return {
        "symbol": norm_sym,
        "retrieved_data": {
            "quote": quote_dict,
            "fundamentals": fundamentals,
            "technicals": technicals,
            "events": market_events,
            "news": news_items,
            "portfolio": portfolio_context,
        },
        "prompt_context_text": prompt_context_text,
        "citations": citations,
        "timestamp": now_str,
    }
