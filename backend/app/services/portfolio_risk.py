"""Portfolio Risk Analysis Engine.

Calculates:
- Individual stock allocation percentages
- Top holding concentration & Herfindahl-Hirschman Index (HHI)
- Weighted historical portfolio daily returns
- Annualized portfolio volatility (sigma = daily_std * sqrt(252))
- Portfolio Maximum Drawdown (MDD) from cumulative wealth index
- Stock-wise individual annualized volatilities
- Portfolio Beta (beta = Cov(Rp, Rm) / Var(Rm)) against NIFTY 50 benchmark
- Deterministic multi-factor risk classifications with transparent numerical thresholds.

Important:
No portfolio is ever labeled as 'safe' or 'guaranteed'. All metrics are mathematical
estimations based on historical closing prices.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
import math

from backend.app.services.market_service import get_stock_history_df

# Default configurable thresholds
RISK_THRESHOLDS = {
    "concentration": {
        "low_max_top_holding": 25.0,     # <= 25% is Low concentration
        "mod_max_top_holding": 40.0,     # 25% - 40% is Moderate
        "hhi_well_diversified": 1500.0,  # HHI < 1500 is diversified
        "hhi_moderately_concentrated": 2500.0,
    },
    "volatility": {
        "low_max_annual_pct": 15.0,      # < 15% is Low volatility
        "mod_max_annual_pct": 25.0,      # 15% - 25% is Moderate
    },
    "drawdown": {
        "low_max_mdd_pct": 10.0,         # < 10% is Low drawdown
        "mod_max_mdd_pct": 20.0,         # 10% - 20% is Moderate
    },
}


def calculate_portfolio_risk(
    holdings: List[Dict[str, Any]],
    period: str = "6mo",
    custom_history_map: Optional[Dict[str, pd.DataFrame]] = None,
    benchmark_symbol: str = "^NSEI",
    custom_benchmark_df: Optional[pd.DataFrame] = None,
    thresholds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Computes rigorous portfolio risk analytics using historical prices.

    Args:
        holdings: List of active holdings with 'symbol' and 'current_value' or 'weight_pct'
        period: Timeframe for historical price series ('3mo', '6mo', '1y')
        custom_history_map: Optional pre-loaded DataFrames for deterministic unit testing
        benchmark_symbol: Benchmark ticker for Beta calculation (default: ^NSEI / NIFTY 50)
        custom_benchmark_df: Optional benchmark DataFrame for unit testing
        thresholds: Configurable risk thresholds
    """
    cfg = thresholds or RISK_THRESHOLDS
    active_holdings = [h for h in holdings if h.get("total_quantity", 0) > 0 or h.get("current_value", 0) > 0]

    # Handle empty portfolio
    if not active_holdings:
        return {
            "is_empty": True,
            "message": "Portfolio contains no active holdings.",
            "risk_score": 0.0,
            "risk_level": "UNASSESSED",
            "concentration": {
                "top_holding_symbol": None,
                "top_holding_weight_pct": 0.0,
                "top_3_weight_pct": 0.0,
                "hhi": 0.0,
                "effective_n": 0.0,
                "classification": "UNASSESSED",
            },
            "volatility": {
                "annualized_portfolio_volatility_pct": 0.0,
                "daily_portfolio_volatility_pct": 0.0,
                "classification": "UNASSESSED",
                "stock_volatilities": [],
            },
            "drawdown": {
                "maximum_drawdown_pct": 0.0,
                "peak_date": None,
                "trough_date": None,
                "classification": "UNASSESSED",
            },
            "benchmark_beta": None,
            "has_benchmark": False,
            "sessions_analyzed": 0,
            "disclaimer": "No investment recommendations or risk guarantees provided.",
        }

    # Step 1: Calculate Portfolio Weights
    total_val = sum(float(h.get("current_value", 0.0)) for h in active_holdings)
    weights: Dict[str, float] = {}

    for h in active_holdings:
        sym = h["symbol"].upper()
        if total_val > 0:
            w = float(h.get("current_value", 0.0)) / total_val
        elif "weight_pct" in h:
            w = float(h["weight_pct"]) / 100.0
        else:
            w = 1.0 / len(active_holdings)
        weights[sym] = w

    # Step 2: Concentration Metrics
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top_sym, top_w = sorted_weights[0]
    top_holding_pct = top_w * 100.0
    top_3_pct = sum(w for _, w in sorted_weights[:3]) * 100.0

    # Herfindahl-Hirschman Index (sum of squared percentage weights: 0 to 10,000)
    hhi = sum((w * 100.0) ** 2 for _, w in weights.items())
    # Effective Number of Assets = 1 / sum(w^2)
    sum_sq_w = sum(w ** 2 for _, w in weights.items())
    effective_n = (1.0 / sum_sq_w) if sum_sq_w > 0 else float(len(weights))

    # Concentration classification
    conc_cfg = cfg.get("concentration", RISK_THRESHOLDS["concentration"])
    if top_holding_pct <= conc_cfg["low_max_top_holding"] and hhi <= conc_cfg["hhi_well_diversified"]:
        conc_class = "LOW_CONCENTRATION"
    elif top_holding_pct <= conc_cfg["mod_max_top_holding"] or hhi <= conc_cfg["hhi_moderately_concentrated"]:
        conc_class = "MODERATE_CONCENTRATION"
    else:
        conc_class = "HIGH_CONCENTRATION"

    # Step 3: Fetch Historical Price Series for each holding
    price_series: Dict[str, pd.Series] = {}
    stock_vols: List[Dict[str, Any]] = []

    for sym in weights.keys():
        df: Optional[pd.DataFrame] = None
        if custom_history_map and sym in custom_history_map:
            df = custom_history_map[sym]
        else:
            try:
                df, _, _ = get_stock_history_df(sym, period=period, interval="1d")
            except Exception:
                df = None

        if df is not None and not df.empty and "close" in df.columns:
            df = df.copy()
            if "timestamp" in df.columns:
                df["date"] = df["timestamp"].astype(str).str.split("T").str[0].str.split(" ").str[0]
                df = df.drop_duplicates(subset=["date"]).sort_values("date")
                s = pd.Series(df["close"].values, index=df["date"])
            else:
                s = df["close"]
            price_series[sym] = s

    # Check for sufficient historical price data
    if not price_series or all(len(s) < 3 for s in price_series.values()):
        return {
            "is_empty": False,
            "insufficient_data": True,
            "message": "Insufficient historical trading sessions available for volatility modeling.",
            "risk_score": 50.0,
            "risk_level": "MODERATE",
            "concentration": {
                "top_holding_symbol": top_sym,
                "top_holding_weight_pct": round(top_holding_pct, 2),
                "top_3_weight_pct": round(top_3_pct, 2),
                "hhi": round(hhi, 2),
                "effective_n": round(effective_n, 2),
                "classification": conc_class,
            },
            "volatility": {
                "annualized_portfolio_volatility_pct": 0.0,
                "daily_portfolio_volatility_pct": 0.0,
                "classification": "INSUFFICIENT_DATA",
                "stock_volatilities": [],
            },
            "drawdown": {
                "maximum_drawdown_pct": 0.0,
                "peak_date": None,
                "trough_date": None,
                "classification": "INSUFFICIENT_DATA",
            },
            "benchmark_beta": None,
            "has_benchmark": False,
            "sessions_analyzed": 0,
            "disclaimer": "Quantitative estimation only. No guarantee of future returns.",
        }

    # Step 4: Align Historical Closes Across All Portfolio Assets
    combined_prices = pd.DataFrame(price_series)
    combined_prices = combined_prices.dropna()  # Inner join on aligned trading dates

    if len(combined_prices) < 3:
        # Fallback with forward fill if inner join too sparse
        combined_prices = pd.DataFrame(price_series).ffill().bfill().dropna()

    sessions_count = len(combined_prices)

    if sessions_count < 3:
        return {
            "is_empty": False,
            "insufficient_data": True,
            "message": "Fewer than 3 overlapping trading sessions found across portfolio constituents.",
            "risk_score": 50.0,
            "risk_level": "MODERATE",
            "concentration": {
                "top_holding_symbol": top_sym,
                "top_holding_weight_pct": round(top_holding_pct, 2),
                "top_3_weight_pct": round(top_3_pct, 2),
                "hhi": round(hhi, 2),
                "effective_n": round(effective_n, 2),
                "classification": conc_class,
            },
            "volatility": {
                "annualized_portfolio_volatility_pct": 0.0,
                "daily_portfolio_volatility_pct": 0.0,
                "classification": "INSUFFICIENT_DATA",
                "stock_volatilities": [],
            },
            "drawdown": {
                "maximum_drawdown_pct": 0.0,
                "peak_date": None,
                "trough_date": None,
                "classification": "INSUFFICIENT_DATA",
            },
            "benchmark_beta": None,
            "has_benchmark": False,
            "sessions_analyzed": sessions_count,
            "disclaimer": "Quantitative estimation only. No guarantee of future returns.",
        }

    # Step 5: Compute Daily Returns for each asset
    daily_returns = combined_prices.pct_change().dropna()

    # Calculate individual stock annualized volatility
    for sym in combined_prices.columns:
        w = weights.get(sym, 0.0)
        ret_s = daily_returns[sym]
        std_daily = float(ret_s.std(ddof=1)) if len(ret_s) > 1 else 0.0
        ann_vol = std_daily * math.sqrt(252) * 100.0
        stock_vols.append({
            "symbol": sym,
            "weight_pct": round(w * 100.0, 2),
            "annualized_volatility_pct": round(ann_vol, 2),
            "daily_volatility_pct": round(std_daily * 100.0, 2),
        })

    # Step 6: Compute WEIGHTED Portfolio Daily Returns: Rp,t = Sum(wi * Ri,t)
    # Strictly use weighted portfolio returns as requested by prompt
    aligned_weights = np.array([weights.get(col, 0.0) for col in daily_returns.columns])
    # Normalize weights across available columns if any were dropped
    w_sum = aligned_weights.sum()
    if w_sum > 0:
        aligned_weights = aligned_weights / w_sum

    portfolio_daily_returns = daily_returns.dot(aligned_weights)

    # Step 7: Portfolio Volatility (Annualized)
    daily_port_std = float(portfolio_daily_returns.std(ddof=1)) if len(portfolio_daily_returns) > 1 else 0.0
    annualized_port_vol = daily_port_std * math.sqrt(252) * 100.0

    vol_cfg = cfg.get("volatility", RISK_THRESHOLDS["volatility"])
    if annualized_port_vol <= vol_cfg["low_max_annual_pct"]:
        vol_class = "LOW_VOLATILITY"
    elif annualized_port_vol <= vol_cfg["mod_max_annual_pct"]:
        vol_class = "MODERATE_VOLATILITY"
    else:
        vol_class = "HIGH_VOLATILITY"

    # Step 8: Portfolio Maximum Drawdown (MDD)
    # Wealth Index: W_0 = 100, W_t = W_{t-1} * (1 + R_p,t)
    wealth_index = (1.0 + portfolio_daily_returns).cumprod() * 100.0
    rolling_peak = wealth_index.cummax()
    drawdown_series = (wealth_index - rolling_peak) / rolling_peak

    min_dd = float(drawdown_series.min()) if not drawdown_series.empty else 0.0
    mdd_pct = abs(min_dd) * 100.0

    # Locate peak and trough dates
    peak_date = None
    trough_date = None
    if not drawdown_series.empty:
        trough_idx = drawdown_series.idxmin()
        trough_date = str(trough_idx)
        peak_idx = wealth_index.loc[:trough_idx].idxmax()
        peak_date = str(peak_idx)

    dd_cfg = cfg.get("drawdown", RISK_THRESHOLDS["drawdown"])
    if mdd_pct <= dd_cfg["low_max_mdd_pct"]:
        dd_class = "LOW_DRAWDOWN"
    elif mdd_pct <= dd_cfg["mod_max_mdd_pct"]:
        dd_class = "MODERATE_DRAWDOWN"
    else:
        dd_class = "SIGNIFICANT_DRAWDOWN"

    # Step 9: Benchmark Beta against NIFTY 50 (if available)
    portfolio_beta: Optional[float] = None
    has_benchmark = False

    bench_df: Optional[pd.DataFrame] = None
    if custom_benchmark_df is not None:
        bench_df = custom_benchmark_df
    else:
        try:
            bench_df, _, _ = get_stock_history_df(benchmark_symbol, period=period, interval="1d")
        except Exception:
            bench_df = None

    if bench_df is not None and not bench_df.empty and "close" in bench_df.columns:
        if "timestamp" in bench_df.columns:
            bench_df["date"] = bench_df["timestamp"].astype(str).str.split("T").str[0].str.split(" ").str[0]
            bench_df = bench_df.drop_duplicates(subset=["date"]).sort_values("date")
            bench_series = pd.Series(bench_df["close"].values, index=bench_df["date"])
        else:
            bench_series = bench_df["close"]

        bench_returns = bench_series.pct_change().dropna()
        # Align with portfolio returns
        joint_ret = pd.DataFrame({
            "port": portfolio_daily_returns,
            "bench": bench_returns,
        }).dropna()

        if len(joint_ret) >= 10:
            cov = float(joint_ret["port"].cov(joint_ret["bench"]))
            var_bench = float(joint_ret["bench"].var())
            if var_bench > 1e-12:
                portfolio_beta = round(cov / var_bench, 2)
                has_benchmark = True

    # Step 10: Composite Risk Score (0 to 100)
    # Volatility component: 0% vol -> 0 score, 35% vol -> 100 score
    vol_score = min(100.0, max(0.0, (annualized_port_vol / 35.0) * 100.0))
    # Drawdown component: 0% mdd -> 0 score, 30% mdd -> 100 score
    dd_score = min(100.0, max(0.0, (mdd_pct / 30.0) * 100.0))
    # Concentration component: HHI 1000 -> 0 score, HHI 5000 -> 100 score
    conc_score = min(100.0, max(0.0, ((hhi - 1000.0) / 4000.0) * 100.0))

    composite_score = round(0.35 * vol_score + 0.35 * dd_score + 0.30 * conc_score, 1)

    if composite_score < 35.0:
        overall_risk_level = "LOW_RISK"
    elif composite_score <= 65.0:
        overall_risk_level = "MODERATE_RISK"
    else:
        overall_risk_level = "ELEVATED_RISK"

    return {
        "is_empty": False,
        "insufficient_data": False,
        "risk_score": composite_score,
        "risk_level": overall_risk_level,
        "concentration": {
            "top_holding_symbol": top_sym,
            "top_holding_weight_pct": round(top_holding_pct, 2),
            "top_3_weight_pct": round(top_3_pct, 2),
            "hhi": round(hhi, 2),
            "effective_n": round(effective_n, 2),
            "classification": conc_class,
            "thresholds": conc_cfg,
        },
        "volatility": {
            "annualized_portfolio_volatility_pct": round(annualized_port_vol, 2),
            "daily_portfolio_volatility_pct": round(daily_port_std * 100.0, 2),
            "classification": vol_class,
            "stock_volatilities": sorted(stock_vols, key=lambda x: x["weight_pct"], reverse=True),
            "thresholds": vol_cfg,
        },
        "drawdown": {
            "maximum_drawdown_pct": round(mdd_pct, 2),
            "peak_date": peak_date,
            "trough_date": trough_date,
            "classification": dd_class,
            "thresholds": dd_cfg,
        },
        "benchmark_beta": portfolio_beta,
        "has_benchmark": has_benchmark,
        "benchmark_symbol": benchmark_symbol if has_benchmark else None,
        "sessions_analyzed": sessions_count,
        "disclaimer": "Risk metrics are mathematical estimations based on historical OHLCV data. No guarantee of future performance is implied.",
    }
