"""Comprehensive Stock Research Report Generator.

Compiles an institutional-quality 9-section research report for Indian equities:
1. Executive Summary
2. Company Overview & Business Profile
3. Historical Price Performance
4. Comprehensive Fundamental Analysis (TTM/MRQ)
5. Technical Indicator Synthesis & Pivot Levels
6. Historical Market Events & Anomaly Analysis
7. Key Risk Factors & Investment Considerations
8. Data Freshness, Audit Trail & Attribution
9. Objective Neutral Synthesis & Conclusion

Saves generated reports directly into PostgreSQL for persistence, review, and export.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from backend.app.models.research import ResearchReport
from backend.app.services.market_service import normalize_symbol, get_stock_quote, get_stock_history_df
from backend.app.services.fundamentals import get_company_fundamentals
from backend.app.services.technical_analysis import analyze_technical_structure
from backend.app.services.rag_retrieval import retrieve_rag_context


def generate_research_report(
    db: Session,
    symbol: str,
    user_id: int = 1,
    custom_title: Optional[str] = None,
    mock_fundamentals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generates a structured 9-section research dossier and persists it in PostgreSQL.
    """
    norm_sym = normalize_symbol(symbol)
    now_utc = datetime.utcnow()
    now_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    # 1. Quote
    quote = get_stock_quote(norm_sym)
    company_name = quote.name

    # 2. Fundamentals
    fundamentals = get_company_fundamentals(norm_sym, mock_data=mock_fundamentals)

    # 3. Technicals
    technicals = analyze_technical_structure(norm_sym, period="6mo")

    # 4. RAG Context (Events, News, Citations)
    rag_context = retrieve_rag_context(
        symbol=norm_sym,
        db=db,
        user_id=user_id,
        include_portfolio=False,
        mock_fundamentals=mock_fundamentals,
    )
    events_data = rag_context.get("retrieved_data", {}).get("events", [])
    sources_data = rag_context.get("citations", [])

    # 5. Price Performance Calculation
    df_hist, _, _ = get_stock_history_df(norm_sym, period="1y")
    perf_metrics = {
        "current_price": quote.price,
        "previous_close": quote.previous_close,
        "fifty_two_week_high": quote.fifty_two_week_high,
        "fifty_two_week_low": quote.fifty_two_week_low,
        "return_1mo_pct": None,
        "return_3mo_pct": None,
        "return_6mo_pct": None,
        "return_1y_pct": None,
    }
    if not df_hist.empty and len(df_hist) >= 5:
        curr_c = df_hist["close"].iloc[-1]
        if len(df_hist) >= 22:
            perf_metrics["return_1mo_pct"] = round(((curr_c - df_hist["close"].iloc[-22]) / df_hist["close"].iloc[-22]) * 100.0, 2)
        if len(df_hist) >= 66:
            perf_metrics["return_3mo_pct"] = round(((curr_c - df_hist["close"].iloc[-66]) / df_hist["close"].iloc[-66]) * 100.0, 2)
        if len(df_hist) >= 126:
            perf_metrics["return_6mo_pct"] = round(((curr_c - df_hist["close"].iloc[-126]) / df_hist["close"].iloc[-126]) * 100.0, 2)
        if len(df_hist) >= 250:
            perf_metrics["return_1y_pct"] = round(((curr_c - df_hist["close"].iloc[0]) / df_hist["close"].iloc[0]) * 100.0, 2)

    # 6. Overview Section
    val = fundamentals.get("valuation", {})
    gro = fundamentals.get("growth", {})
    pro = fundamentals.get("profitability", {})
    fin = fundamentals.get("financial_health", {})

    overview_data = {
        "symbol": norm_sym,
        "company_name": company_name,
        "exchange": quote.exchange,
        "sector": quote.sector,
        "industry": fundamentals.get("overview", {}).get("industry", "Unknown Industry"),
        "business_summary": fundamentals.get("overview", {}).get("business_summary", "Business summary unavailable."),
        "website": fundamentals.get("overview", {}).get("website", ""),
        "price_performance": perf_metrics,
    }

    # 7. Risk Factors
    risk_factors: List[Dict[str, str]] = []
    # Valuation risk
    pe_t = val.get("pe_trailing")
    if pe_t and pe_t > 40.0:
        risk_factors.append({
            "category": "Valuation Premium",
            "severity": "HIGH",
            "description": f"Trailing P/E of {pe_t}x trades at a rich multiple, leaving little margin of safety if quarterly earnings fail to beat expectations.",
        })
    elif pe_t and pe_t > 25.0:
        risk_factors.append({
            "category": "Moderate Valuation",
            "severity": "MEDIUM",
            "description": f"Trailing P/E of {pe_t}x is moderately elevated compared to broader market averages.",
        })

    # Debt risk
    de = fin.get("debt_to_equity")
    if de and de > 1.5:
        risk_factors.append({
            "category": "Leverage / Solvency",
            "severity": "HIGH",
            "description": f"Debt-to-Equity ratio of {de}x indicates substantial financial leverage and sensitivity to interest rate cycles.",
        })
    elif de and de > 0.8:
        risk_factors.append({
            "category": "Moderate Leverage",
            "severity": "MEDIUM",
            "description": f"Debt-to-Equity ratio stands at {de}x with manageable interest coverage.",
        })

    # Technical risk
    tech_sent = technicals.get("overall_sentiment", "NEUTRAL")
    rsi_val = technicals.get("indicators", {}).get("rsi_14")
    if rsi_val and rsi_val >= 70.0:
        risk_factors.append({
            "category": "Technical Overbought",
            "severity": "MEDIUM",
            "description": f"Wilder RSI (14) at {rsi_val} indicates short-term momentum exhaustion and increased probability of a pullback.",
        })
    if tech_sent == "BEARISH":
        risk_factors.append({
            "category": "Technical Headwinds",
            "severity": "HIGH",
            "description": "Moving averages and MACD indicate prevailing downward momentum below key trend benchmarks.",
        })

    if not risk_factors:
        risk_factors.append({
            "category": "Macro & Sector",
            "severity": "LOW",
            "description": "Standard market risk and sensitivity to general economic and industry trends.",
        })

    # 8. Report Title & Executive Summary
    title = custom_title or f"Institutional Equity Research Report: {company_name} ({norm_sym})"
    summary = (
        f"{company_name} ({norm_sym}) is currently trading at ₹{quote.price:,.2f} on the {quote.exchange}. "
        f"The stock exhibits a {tech_sent.lower()} technical posture with RSI at {rsi_val or 'N/A'}. "
        f"Fundamentals reflect a Market Capitalization of ₹{val.get('market_cap_formatted', 'N/A')}, "
        f"trailing P/E of {pe_t or 'N/A'}x, and YoY revenue growth of {gro.get('revenue_growth_yoy_pct', 'N/A')}%. "
        f"Key support rests at ₹{technicals.get('support_levels', {}).get('s1', 'N/A')}, while primary resistance is ₹{technicals.get('resistance_levels', {}).get('r1', 'N/A')}."
    )

    # 9. Objective Neutral Conclusion
    conclusion = (
        f"{company_name} presents a multi-faceted profile. On fundamental metrics, the company's operating margin of "
        f"{pro.get('operating_margin_pct', 'N/A')}% and Return on Equity of {pro.get('return_on_equity_pct', 'N/A')}% "
        f"demonstrate its operational scale. From a technical perspective, the stock is currently classified as {tech_sent}, "
        f"with immediate pivot support at ₹{technicals.get('support_levels', {}).get('pivot', 'N/A')} and resistance at "
        f"₹{technicals.get('resistance_levels', {}).get('r1', 'N/A')}. Investors should weigh these catalysts against identified risks, "
        f"including valuation multiples and broader macroeconomic conditions. "
        f"This report does not constitute a buy or sell recommendation."
    )

    # Persist Report in PostgreSQL
    report_db = ResearchReport(
        user_id=user_id,
        symbol=norm_sym,
        company_name=company_name,
        title=title,
        summary=summary,
        overview_data=overview_data,
        fundamentals_data=fundamentals,
        technical_data=technicals,
        events_data=events_data,
        risk_factors=risk_factors,
        sources=sources_data,
        conclusion=conclusion,
        created_at=now_utc,
    )
    db.add(report_db)
    db.commit()
    db.refresh(report_db)

    return {
        "id": report_db.id,
        "symbol": norm_sym,
        "company_name": company_name,
        "title": title,
        "summary": summary,
        "overview": overview_data,
        "fundamentals": fundamentals,
        "technicals": technicals,
        "events": events_data,
        "risk_factors": risk_factors,
        "sources": sources_data,
        "conclusion": conclusion,
        "created_at": report_db.created_at.isoformat() + "Z",
    }


def get_saved_reports(db: Session, user_id: int, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves saved research reports for a user."""
    query = db.query(ResearchReport).filter(ResearchReport.user_id == user_id)
    if symbol:
        norm_sym = normalize_symbol(symbol)
        query = query.filter(ResearchReport.symbol == norm_sym)
    reports = query.order_by(ResearchReport.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "company_name": r.company_name,
            "title": r.title,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
        }
        for r in reports
    ]


def get_report_by_id(db: Session, report_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a full saved research report by ID with user isolation."""
    report = (
        db.query(ResearchReport)
        .filter(ResearchReport.id == report_id, ResearchReport.user_id == user_id)
        .first()
    )
    if not report:
        return None
    return {
        "id": report.id,
        "symbol": report.symbol,
        "company_name": report.company_name,
        "title": report.title,
        "summary": report.summary,
        "overview": report.overview_data,
        "fundamentals": report.fundamentals_data,
        "technicals": report.technical_data,
        "events": report.events_data,
        "risk_factors": report.risk_factors,
        "sources": report.sources,
        "conclusion": report.conclusion,
        "created_at": report.created_at.isoformat() + "Z" if report.created_at else None,
    }
