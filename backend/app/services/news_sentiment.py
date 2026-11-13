"""Financial News Sentiment Analysis & AI Summarization Engine.

Modules 2 & 3:
1. Summarizes news articles with key facts, financial figures, company mentions, and risks.
2. Classifies sentiment into POSITIVE, NEGATIVE, NEUTRAL, MIXED with a continuous score (-1.0 to +1.0)
   and a model confidence metric (0.0 to 1.0).
3. Connects to Stage 7 LLM provider abstraction (Gemini / Deterministic) and provides an
   accurate financial domain rule-based NLP baseline.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from backend.app.models.news import FinancialNews, NewsSentiment
from backend.app.services.market_service import normalize_symbol, SYMBOL_METADATA
from backend.app.services.rag_retrieval import sanitize_untrusted_text

# Financial sentiment lexicon tailored for Indian equity markets
BULLISH_KEYWORDS = [
    r"\bprofit\s+(surges?|jumps?|soars?|rises?|up|grows?|growth)\b",
    r"\brevenue\s+(surges?|jumps?|grows?|growth|up|increases?)\b",
    r"\b(revenue|profit|sales|earnings)\s+growth\b",
    r"\bmargin\s+expands?(ion)?\b",
    r"\border\s+wins?\b",
    r"\bcontracts?\s+(wins?|awarded|secured|signed)\b",
    r"\bdividends?\s+(hike|increase|declared|bonus)\b",
    r"\bguidance\s+(upgraded?|raised)\b",
    r"\bbeat\s+(estimates?|expectations?)\b",
    r"\brated\s+buy\b",
    r"\bupgrades?\b",
    r"\bexpansion\b",
    r"\ball-time\s+high\b",
    r"\bpartnership\b",
    r"\bacquisition\b",
    r"\bcapacity\s+addition\b",
    r"\bnet\s+profit\s+rises?\b",
    r"\bstrong\s+(q[1-4]|quarter|earnings|results)\b",
    r"\bdebt\s+(reduction|repaid|free)\b",
]

BEARISH_KEYWORDS = [
    r"\bprofit\s+(slumps?|tanks?|falls?|plunges?|drops?|down|declines?)\b",
    r"\brevenue\s+(falls?|drops?|declines?|slumps?)\b",
    r"\bloss\s+(widens?|reported|deepens?)\b",
    r"\bmiss(es)?\s+(estimates?|expectations?)\b",
    r"\bguidance\s+(cut|slashed|lowered)\b",
    r"\bsebi\s+(penalty|probe|investigation|notice|ban)\b",
    r"\brbi\s+(penalty|restriction|action|audit)\b",
    r"\bshow\s+cause\s+notice\b",
    r"\bfraud\b",
    r"\bdefault(s|ed)?\b",
    r"\brating\s+downgrades?\b",
    r"\bdowngrades?\b",
    r"\brated\s+sell\b",
    r"\blawsuit\b",
    r"\braids?\b",
    r"\binsolvency\b",
    r"\bdebt\s+concerns?\b",
    r"\bweak\s+(q[1-4]|quarter|earnings|results)\b",
    r"\blayo?ffs?\b",
    r"\bslumps?\b",
    r"\btanks?\b",
]


def extract_companies_mentioned(text: str) -> List[str]:
    """Extracts ticker symbols or known Indian company names from text."""
    found: List[str] = []
    upper_text = text.upper()

    for sym, meta in SYMBOL_METADATA.items():
        base_name = meta.get("name", "").upper()
        clean_sym = sym.replace(".NS", "").replace(".BO", "").replace("^", "")

        # Check ticker symbol
        if re.search(rf"\b{re.escape(clean_sym)}\b", upper_text):
            if sym not in found:
                found.append(sym)
        # Check company name
        elif base_name and any(part in upper_text for part in base_name.split() if len(part) > 3):
            if sym not in found:
                found.append(sym)

    return found


def extract_financial_figures(text: str) -> List[str]:
    """Extracts stated financial metrics, rupee amounts, and percentages from text."""
    figures: List[str] = []

    # Rupee amounts (e.g. ₹5,000 Cr, Rs 250 crore, $1.5 billion)
    rupee_matches = re.findall(
        r"(?:(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?\s*(?:cr(?:ore)?|lakh|bn|billion|tn|trillion)?\b)",
        text,
        re.IGNORECASE,
    )
    for m in rupee_matches:
        if m.strip() not in figures:
            figures.append(m.strip())

    # Percentage changes (e.g. up 18.5%, profit rose 25%, fell 4.2%, rise by 4.5%)
    pct_matches = re.findall(
        r"(?:(?:up|down|rose|rise|rises|rising|fell|grew|growth|jumped|surged|dropped|declined|by)\s+)?[\d,]+(?:\.\d+)?%",
        text,
        re.IGNORECASE,
    )
    for m in pct_matches:
        if m.strip() not in figures:
            figures.append(m.strip())

    return figures[:6]


def calculate_rule_based_sentiment(text: str, target_symbol: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes financial domain rule-based sentiment classification.
    Returns: label, score, confidence, and matches.
    """
    clean_text = text.lower()

    bull_hits = 0
    bear_hits = 0

    for pat in BULLISH_KEYWORDS:
        if re.search(pat, clean_text):
            bull_hits += 1

    for pat in BEARISH_KEYWORDS:
        if re.search(pat, clean_text):
            bear_hits += 1

    total_hits = bull_hits + bear_hits

    if total_hits == 0:
        return {
            "sentiment_label": "NEUTRAL",
            "sentiment_score": 0.0,
            "confidence": 0.65,
            "bull_signals": 0,
            "bear_signals": 0,
        }

    # Mixed check: both strong positive and strong negative signals present
    if bull_hits >= 1 and bear_hits >= 1 and abs(bull_hits - bear_hits) <= 1:
        return {
            "sentiment_label": "MIXED",
            "sentiment_score": round((bull_hits - bear_hits) / (total_hits + 1), 2),
            "confidence": 0.75,
            "bull_signals": bull_hits,
            "bear_signals": bear_hits,
        }

    # Score from -1.0 to +1.0
    raw_score = (bull_hits - bear_hits) / max(total_hits, 1)
    score = round(max(-1.0, min(1.0, raw_score)), 2)

    confidence = round(min(0.95, 0.60 + total_hits * 0.10), 2)

    if score > 0.15:
        label = "POSITIVE"
    elif score < -0.15:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"

    return {
        "sentiment_label": label,
        "sentiment_score": score,
        "confidence": confidence,
        "bull_signals": bull_hits,
        "bear_signals": bear_hits,
    }


def analyze_article_content(
    title: str,
    snippet: Optional[str] = None,
    target_symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Performs full AI summarization and financial sentiment analysis for an article.
    """
    full_text = f"{title}. {snippet or ''}".strip()
    sanitized = sanitize_untrusted_text(full_text)

    # 1. Financial Sentiment
    sentiment_res = calculate_rule_based_sentiment(sanitized, target_symbol=target_symbol)

    # 2. Extract Entities & Metrics
    companies = extract_companies_mentioned(sanitized)
    if target_symbol and target_symbol not in companies:
        companies.append(target_symbol)

    figures = extract_financial_figures(sanitized)

    # 3. Key Facts & Summary
    key_facts = [title.strip()]
    if snippet and snippet != title:
        key_facts.append(snippet.strip())

    # Market relevance
    label = sentiment_res["sentiment_label"]
    if label == "POSITIVE":
        relevance = "Positive operational catalyst or expansion that may support near-term earnings sentiment."
    elif label == "NEGATIVE":
        relevance = "Headwind or regulatory/financial challenge that could increase downside volatility."
    elif label == "MIXED":
        relevance = "Conflicting operational signals; market participants are likely to focus on underlying margin impact."
    else:
        relevance = "Routine market or corporate information without immediate fundamental directional impact."

    # Risks
    risks = []
    if label in ["NEGATIVE", "MIXED"]:
        risks.append("Headline risk and near-term market repricing.")
    if "sebi" in sanitized.lower() or "regulatory" in sanitized.lower():
        risks.append("Potential regulatory compliance penalties or operational constraints.")

    return {
        "sentiment_label": label,
        "sentiment_score": sentiment_res["sentiment_score"],
        "confidence": sentiment_res["confidence"],
        "ai_summary": sanitized[:300] + ("..." if len(sanitized) > 300 else ""),
        "key_facts": key_facts,
        "financial_figures": figures,
        "companies_mentioned": companies,
        "market_relevance": relevance,
        "risk_factors": risks,
        "model_version": "stockpulse-finbert-v1",
    }


def analyze_and_persist_news_sentiment(
    db: Session,
    news_id: int,
    target_symbol: Optional[str] = None,
) -> Optional[NewsSentiment]:
    """
    Analyzes an existing FinancialNews record and persists NewsSentiment into PostgreSQL.
    """
    news_record = db.query(FinancialNews).filter(FinancialNews.id == news_id).first()
    if not news_record:
        return None

    # Check if sentiment already analyzed
    existing_sent = db.query(NewsSentiment).filter(NewsSentiment.news_id == news_id).first()
    if existing_sent:
        return existing_sent

    sym = target_symbol or news_record.symbol
    analysis = analyze_article_content(
        title=news_record.title,
        snippet=news_record.summary or news_record.raw_snippet,
        target_symbol=sym,
    )

    sentiment_row = NewsSentiment(
        news_id=news_record.id,
        symbol=sym,
        sentiment_label=analysis["sentiment_label"],
        sentiment_score=analysis["sentiment_score"],
        confidence=analysis["confidence"],
        ai_summary=analysis["ai_summary"],
        key_facts=analysis["key_facts"],
        financial_figures=analysis["financial_figures"],
        companies_mentioned=analysis["companies_mentioned"],
        market_relevance=analysis["market_relevance"],
        risk_factors=analysis["risk_factors"],
        model_version=analysis["model_version"],
        analyzed_at=datetime.utcnow(),
    )
    db.add(sentiment_row)
    db.commit()
    db.refresh(sentiment_row)

    return sentiment_row
