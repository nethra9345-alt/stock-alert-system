"""Company Fundamental Analysis Service for Indian NSE/BSE Stocks.

Retrieves and validates company financial statements, valuation multiples,
growth metrics, profitability margins, and financial health ratios.

Strict Data Integrity Rules:
- Never fabricate financial numbers or growth percentages.
- Include reporting periods (TTM vs Annual), source attribution, and timestamps.
- Explicitly mark missing metrics as UNAVAILABLE rather than defaulting to zero.
- Handle stale data transparently.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import math
import yfinance as yf

from backend.app.services.market_service import normalize_symbol

# Simple in-memory cache to prevent redundant provider calls: symbol -> (timestamp, data)
_FUNDAMENTALS_CACHE: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}
CACHE_TTL_MINUTES = 15


def get_company_fundamentals(
    symbol: str,
    mock_data: Optional[Dict[str, Any]] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Fetches and standardizes fundamentals data for an NSE/BSE stock ticker.

    Args:
        symbol: Ticker symbol (e.g. 'RELIANCE', 'TCS.NS')
        mock_data: Optional dictionary to mock provider responses in unit tests
        force_refresh: Ignore cache if True
    """
    norm_sym = normalize_symbol(symbol)
    now = datetime.utcnow()

    # Check cache if not mocking and not forced
    if not mock_data and not force_refresh:
        if norm_sym in _FUNDAMENTALS_CACHE:
            cache_time, cached_res = _FUNDAMENTALS_CACHE[norm_sym]
            if now - cache_time < timedelta(minutes=CACHE_TTL_MINUTES):
                return cached_res

    # Use mock data if provided for tests
    if mock_data is not None:
        info = mock_data
    else:
        try:
            ticker = yf.Ticker(norm_sym)
            info = ticker.info or {}
        except Exception as e:
            info = {}

    missing_metrics: List[str] = []

    def safe_extract(key: str, is_pct: bool = False, scale: Optional[float] = None) -> Optional[float]:
        val = info.get(key)
        if val is None or (isinstance(val, (int, float)) and (math.isnan(val) or math.isinf(val))):
            missing_metrics.append(key)
            return None
        try:
            f_val = float(val)
            if scale:
                f_val = f_val * scale
            if is_pct:
                # If provider returns 0.0875 for 8.75%
                if abs(f_val) <= 1.0 and key in ["returnOnEquity", "returnOnAssets", "operatingMargins", "profitMargins", "revenueGrowth", "earningsGrowth"]:
                    f_val = f_val * 100.0
            return round(f_val, 2)
        except (ValueError, TypeError):
            missing_metrics.append(key)
            return None

    # Overview
    company_name = info.get("longName") or info.get("shortName") or norm_sym
    sector = info.get("sector") or "Unknown Sector"
    industry = info.get("industry") or "Unknown Industry"
    business_summary = info.get("longBusinessSummary") or info.get("description") or "Company overview unavailable."
    website = info.get("website") or ""
    currency = info.get("financialCurrency") or info.get("currency") or "INR"

    # Valuation
    market_cap = info.get("marketCap")
    market_cap_float = float(market_cap) if market_cap and not math.isnan(float(market_cap)) else None

    trailing_pe = safe_extract("trailingPE")
    forward_pe = safe_extract("forwardPE")
    price_to_book = safe_extract("priceToBook")
    price_to_sales = safe_extract("priceToSalesTrailing12Months")
    enterprise_value = info.get("enterpriseValue")
    enterprise_value_float = float(enterprise_value) if enterprise_value and not math.isnan(float(enterprise_value)) else None
    ev_to_ebitda = safe_extract("enterpriseToEbitda")

    # Financial Performance (TTM)
    total_revenue = info.get("totalRevenue")
    total_revenue_float = float(total_revenue) if total_revenue and not math.isnan(float(total_revenue)) else None

    revenue_growth_yoy = safe_extract("revenueGrowth", is_pct=True)

    net_profit = info.get("netIncomeToCommon") or info.get("netIncome")
    net_profit_float = float(net_profit) if net_profit and not math.isnan(float(net_profit)) else None

    profit_growth_yoy = safe_extract("earningsGrowth", is_pct=True)
    trailing_eps = safe_extract("trailingEps")
    forward_eps = safe_extract("forwardEps")

    # Margins & Profitability
    roe = safe_extract("returnOnEquity", is_pct=True)
    roa = safe_extract("returnOnAssets", is_pct=True)
    operating_margin = safe_extract("operatingMargins", is_pct=True)
    net_margin = safe_extract("profitMargins", is_pct=True)

    # ROCE (Return on Capital Employed)
    # Formula: EBIT / (Total Debt + Stockholder Equity)
    # If explicit or calculable from EBITDA and debt/equity
    roce: Optional[float] = None
    ebitda = info.get("ebitda")
    total_debt = info.get("totalDebt")
    book_value = info.get("bookValue")
    shares = info.get("sharesOutstanding")

    if ebitda and total_debt is not None and book_value and shares:
        try:
            equity = float(book_value) * float(shares)
            capital_employed = float(total_debt) + equity
            if capital_employed > 0:
                roce = round((float(ebitda) / capital_employed) * 100.0, 2)
        except Exception:
            roce = None
    if roce is None:
        missing_metrics.append("roce")

    # Financial Health & Debt
    debt_to_equity = safe_extract("debtToEquity")  # Provider usually returns e.g. 44.32 (means 44.3%)
    current_ratio = safe_extract("currentRatio")
    quick_ratio = safe_extract("quickRatio")
    free_cash_flow = info.get("freeCashflow")
    free_cash_flow_float = float(free_cash_flow) if free_cash_flow and not math.isnan(float(free_cash_flow)) else None

    # Dividends
    dividend_yield = safe_extract("dividendYield", is_pct=True)

    # Data freshness & reporting period determination
    fiscal_year_end = info.get("lastFiscalYearEnd")
    most_recent_quarter = info.get("mostRecentQuarter")
    reporting_period = "TTM (Trailing Twelve Months)"
    if most_recent_quarter:
        try:
            q_date = datetime.fromtimestamp(most_recent_quarter)
            reporting_period = f"TTM / MRQ ({q_date.strftime('%b %Y')})"
        except Exception:
            pass

    # Check for stale data (> 18 months old)
    data_freshness = "CURRENT"
    if fiscal_year_end:
        try:
            fy_date = datetime.fromtimestamp(fiscal_year_end)
            if (now - fy_date).days > 550:
                data_freshness = "STALE"
        except Exception:
            pass

    if not info or len(info) <= 2:
        data_freshness = "UNAVAILABLE"

    result = {
        "symbol": norm_sym,
        "company_name": company_name,
        "sector": sector,
        "industry": industry,
        "business_summary": business_summary,
        "website": website,
        "currency": currency,
        "reporting_period": reporting_period,
        "data_source": "NSE / Corporate Filings via Yahoo Finance",
        "retrieved_at": now.isoformat(),
        "data_freshness": data_freshness,
        "overview": {
            "company_name": company_name,
            "sector": sector,
            "industry": industry,
            "business_summary": business_summary,
            "website": website,
        },
        "valuation": {
            "market_cap": market_cap_float,
            "market_cap_formatted": f"{round(market_cap_float / 1e12, 2)}T" if market_cap_float else "UNAVAILABLE",
            "trailing_pe": trailing_pe,
            "pe_trailing": trailing_pe,
            "forward_pe": forward_pe,
            "pe_forward": forward_pe,
            "price_to_book": price_to_book,
            "price_to_sales": price_to_sales,
            "enterprise_value": enterprise_value_float,
            "ev_to_ebitda": ev_to_ebitda,
            "reporting_period": reporting_period,
        },
        "financial_performance": {
            "total_revenue": total_revenue_float,
            "revenue_growth_yoy_pct": revenue_growth_yoy,
            "net_profit": net_profit_float,
            "profit_growth_yoy_pct": profit_growth_yoy,
            "trailing_eps": trailing_eps,
            "forward_eps": forward_eps,
        },
        "growth": {
            "revenue_growth_yoy_pct": revenue_growth_yoy,
            "profit_growth_yoy_pct": profit_growth_yoy,
        },
        "profitability": {
            "roe_pct": roe,
            "return_on_equity_pct": roe,
            "roa_pct": roa,
            "roce_pct": roce,
            "operating_margin_pct": operating_margin,
            "net_margin_pct": net_margin,
            "free_cash_flow": free_cash_flow_float,
        },
        "financial_health": {
            "debt_to_equity": debt_to_equity,
            "debt_to_equity_pct": debt_to_equity,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "dividend_yield_pct": dividend_yield,
            "currency": currency,
        },
        "dividends": {
            "dividend_yield_pct": dividend_yield,
        },
        "missing_metrics": list(set(missing_metrics)),
        "disclaimer": "Fundamental ratios reflect publicly disclosed financial statements. Never guaranteed.",
    }

    if not mock_data:
        _FUNDAMENTALS_CACHE[norm_sym] = (now, result)

    return result
