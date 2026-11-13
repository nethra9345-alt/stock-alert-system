"""Stock Comparison Engine for Indian NSE/BSE Equities.

Enables multi-stock side-by-side analysis comparing:
1. Valuation Multiples & Market Capitalization
2. Growth & Profitability Ratios (TTM)
3. Balance Sheet Strength & Leverage
4. Technical Momentum & Trend Status
5. Normalized Historical Performance Series for unified charting
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np

from backend.app.services.market_service import normalize_symbol, get_stock_history_df, get_stock_quote
from backend.app.services.fundamentals import get_company_fundamentals
from backend.app.services.technical_analysis import analyze_technical_structure


def compare_stocks(
    symbols: List[str],
    period: str = "6mo",
    mock_data_dict: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Performs multi-stock comparative analysis across fundamentals, technicals, and normalized returns.

    Args:
        symbols: List of ticker symbols (min 2, max 5 recommended)
        period: Timeframe for normalized price history ('1mo', '3mo', '6mo', '1y')
        mock_data_dict: Optional dictionary mapping normalized symbol -> mock fundamentals info
    """
    if not symbols or len(symbols) < 2:
        raise ValueError("At least two stock symbols are required for comparison.")

    norm_symbols = [normalize_symbol(s) for s in symbols]
    # Deduplicate while preserving order
    unique_symbols: List[str] = []
    for s in norm_symbols:
        if s not in unique_symbols:
            unique_symbols.append(s)

    fundamentals_list: List[Dict[str, Any]] = []
    technicals_list: List[Dict[str, Any]] = []
    quotes_list: List[Dict[str, Any]] = []
    histories: Dict[str, pd.DataFrame] = {}

    for sym in unique_symbols:
        # Quote
        try:
            q = get_stock_quote(sym)
            quotes_list.append({
                "symbol": sym,
                "name": q.name,
                "price": q.price,
                "change": q.change,
                "change_percent": q.change_percent,
                "exchange": q.exchange,
                "sector": q.sector,
            })
        except Exception:
            quotes_list.append({
                "symbol": sym,
                "name": sym,
                "price": None,
                "change": None,
                "change_percent": None,
                "exchange": "NSE",
                "sector": "Unknown",
            })

        # Fundamentals
        mock_f = mock_data_dict.get(sym) if mock_data_dict else None
        fund = get_company_fundamentals(sym, mock_data=mock_f)
        fundamentals_list.append(fund)

        # Technicals
        tech = analyze_technical_structure(sym, period=period)
        technicals_list.append(tech)

        # History for normalized returns
        df, _, _ = get_stock_history_df(sym, period=period)
        if not df.empty and "timestamp" in df.columns and "close" in df.columns:
            histories[sym] = df[["timestamp", "close"]].rename(columns={"close": sym})

    # Build Normalized Return Series
    normalized_series: List[Dict[str, Any]] = []
    if histories:
        # Merge all dataframes on timestamp (inner join on common trading dates)
        merged = None
        for sym, df_s in histories.items():
            if merged is None:
                merged = df_s
            else:
                merged = pd.merge(merged, df_s, on="timestamp", how="inner")

        if merged is not None and len(merged) > 1:
            merged = merged.sort_values("timestamp").reset_index(drop=True)
            # Rebase to 100 at base date (first common date)
            for sym in histories.keys():
                if sym in merged.columns:
                    base_val = merged[sym].iloc[0]
                    if base_val and base_val > 0:
                        merged[f"{sym}_norm"] = ((merged[sym] / base_val) * 100.0).round(2)
                        merged[f"{sym}_return_pct"] = (((merged[sym] - base_val) / base_val) * 100.0).round(2)
                    else:
                        merged[f"{sym}_norm"] = 100.0
                        merged[f"{sym}_return_pct"] = 0.0

            # Convert to list of records
            for _, row in merged.iterrows():
                pt = {"timestamp": str(row["timestamp"])}
                for sym in histories.keys():
                    if f"{sym}_norm" in row:
                        pt[sym] = row[f"{sym}_norm"]
                        pt[f"{sym}_pct"] = row[f"{sym}_return_pct"]
                        pt[f"{sym}_price"] = row[sym]
                normalized_series.append(pt)

    # Build Comparative Metric Matrix
    metrics_matrix: List[Dict[str, Any]] = []

    def make_row(category: str, metric_name: str, unit: str, key_path: List[str]):
        row: Dict[str, Any] = {
            "category": category,
            "metric": metric_name,
            "unit": unit,
            "values": {},
        }
        for f in fundamentals_list:
            sym = f.get("symbol", "N/A")
            curr = f
            val = None
            for k in key_path:
                if isinstance(curr, dict) and k in curr:
                    curr = curr[k]
                else:
                    curr = None
                    break
            val = curr
            row["values"][sym] = val
        return row

    metrics_matrix.append(make_row("Valuation", "Market Cap", "INR", ["valuation", "market_cap"]))
    metrics_matrix.append(make_row("Valuation", "Trailing P/E", "x", ["valuation", "pe_trailing"]))
    metrics_matrix.append(make_row("Valuation", "Forward P/E", "x", ["valuation", "pe_forward"]))
    metrics_matrix.append(make_row("Valuation", "Price / Book (P/B)", "x", ["valuation", "price_to_book"]))
    metrics_matrix.append(make_row("Valuation", "Price / Sales (P/S)", "x", ["valuation", "price_to_sales"]))
    metrics_matrix.append(make_row("Valuation", "EV / EBITDA", "x", ["valuation", "ev_to_ebitda"]))

    metrics_matrix.append(make_row("Growth", "Revenue Growth (YoY)", "%", ["growth", "revenue_growth_yoy_pct"]))
    metrics_matrix.append(make_row("Growth", "Net Profit Growth (YoY)", "%", ["growth", "profit_growth_yoy_pct"]))

    metrics_matrix.append(make_row("Profitability", "Return on Equity (ROE)", "%", ["profitability", "return_on_equity_pct"]))
    metrics_matrix.append(make_row("Profitability", "ROCE (EBIT / CapEmployed)", "%", ["profitability", "roce_pct"]))
    metrics_matrix.append(make_row("Profitability", "Operating Margin", "%", ["profitability", "operating_margin_pct"]))
    metrics_matrix.append(make_row("Profitability", "Net Margin", "%", ["profitability", "net_margin_pct"]))

    metrics_matrix.append(make_row("Financial Health", "Debt / Equity", "x", ["financial_health", "debt_to_equity"]))
    metrics_matrix.append(make_row("Financial Health", "Current Ratio", "x", ["financial_health", "current_ratio"]))
    metrics_matrix.append(make_row("Dividends", "Dividend Yield", "%", ["dividends", "dividend_yield_pct"]))

    # Synthesize Objective Comparative Summary
    summary_points: List[str] = []
    
    # Valuation check
    pe_vals = [(f["symbol"], f["valuation"]["pe_trailing"]) for f in fundamentals_list if f.get("valuation", {}).get("pe_trailing") is not None]
    if len(pe_vals) >= 2:
        pe_vals.sort(key=lambda x: x[1])
        lowest_pe = pe_vals[0]
        highest_pe = pe_vals[-1]
        summary_points.append(
            f"Valuation: {lowest_pe[0]} trades at a lower trailing P/E ({lowest_pe[1]}x) compared to {highest_pe[0]} ({highest_pe[1]}x)."
        )

    # Growth check
    rev_growth = [(f["symbol"], f["growth"]["revenue_growth_yoy_pct"]) for f in fundamentals_list if f.get("growth", {}).get("revenue_growth_yoy_pct") is not None]
    if len(rev_growth) >= 2:
        rev_growth.sort(key=lambda x: x[1], reverse=True)
        fastest = rev_growth[0]
        slowest = rev_growth[-1]
        summary_points.append(
            f"Topline Growth: {fastest[0]} recorded stronger YoY revenue growth (+{fastest[1]}%) vs {slowest[0]} (+{slowest[1]}%)."
        )

    # Balance Sheet check
    de_vals = [(f["symbol"], f["financial_health"]["debt_to_equity"]) for f in fundamentals_list if f.get("financial_health", {}).get("debt_to_equity") is not None]
    if len(de_vals) >= 2:
        de_vals.sort(key=lambda x: x[1])
        least_leverage = de_vals[0]
        most_leverage = de_vals[-1]
        summary_points.append(
            f"Leverage & Solvency: {least_leverage[0]} maintains a lower Debt-to-Equity ratio ({least_leverage[1]}x) vs {most_leverage[0]} ({most_leverage[1]}x)."
        )

    # Technical momentum check
    tech_signals = [(t["symbol"], t.get("indicators", {}).get("rsi_14"), t.get("overall_sentiment")) for t in technicals_list if t.get("status") == "AVAILABLE"]
    if tech_signals:
        tech_summary = ", ".join([f"{s[0]}: RSI {s[1]} ({s[2]})" for s in tech_signals if s[1] is not None])
        if tech_summary:
            summary_points.append(f"Technical Posture: {tech_summary}.")

    return {
        "symbols": unique_symbols,
        "period": period,
        "quotes": quotes_list,
        "fundamentals": fundamentals_list,
        "technicals": technicals_list,
        "metrics_matrix": metrics_matrix,
        "normalized_series": normalized_series,
        "comparative_summary": summary_points,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

