"""AI Technical Analysis Service for Indian NSE/BSE Stocks.

Synthesizes multiple technical indicators (SMA, EMA, RSI, MACD, Pivot Points, Volatility)
into clear, rule-based algorithmic signals, identifying bullish catalysts, bearish headwinds,
and conflicting technical patterns without future lookahead bias.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np
import pandas as pd

from backend.app.services.market_service import get_stock_history_df, normalize_symbol
from backend.app.services.indicators import compute_technical_indicators


def calculate_pivot_points(high: float, low: float, close: float) -> Dict[str, float]:
    """
    Computes Standard Classic Floor Pivot Points from prior session High, Low, Close.
    P  = (High + Low + Close) / 3
    R1 = 2*P - Low
    S1 = 2*P - High
    R2 = P + (High - Low)
    S2 = P - (High - Low)
    """
    p = (high + low + close) / 3.0
    r1 = 2.0 * p - low
    s1 = 2.0 * p - high
    r2 = p + (high - low)
    s2 = p - (high - low)
    return {
        "pivot": round(p, 2),
        "r1": round(r1, 2),
        "s1": round(s1, 2),
        "r2": round(r2, 2),
        "s2": round(s2, 2),
    }


def compute_historical_volatility(close_series: pd.Series, window: int = 20) -> Optional[float]:
    """Computes 20-session annualized historical volatility."""
    if len(close_series) < window + 1:
        return None
    log_returns = np.log(close_series / close_series.shift(1))
    recent = log_returns.iloc[-window:].dropna()
    if len(recent) < 5:
        return None
    daily_std = float(np.std(recent, ddof=1))
    annualized = daily_std * np.sqrt(252) * 100.0
    return round(annualized, 2)


def analyze_technical_structure(
    symbol: str,
    df: Optional[pd.DataFrame] = None,
    period: str = "6mo",
) -> Dict[str, Any]:
    """
    Performs end-to-end technical analysis and returns a structured synthesis.

    Args:
        symbol: Ticker symbol (e.g. 'RELIANCE.NS')
        df: Optional pre-loaded DataFrame with OHLCV columns (timestamp, open, high, low, close, volume)
        period: Timeframe period if df is not provided (default '6mo')
    """
    norm_sym = normalize_symbol(symbol)

    if df is None:
        raw_df, is_demo, source = get_stock_history_df(norm_sym, period=period)
    else:
        raw_df = df.copy()
        is_demo = False
        source = "test_data"

    if raw_df.empty or len(raw_df) < 5:
        return {
            "symbol": norm_sym,
            "status": "UNAVAILABLE",
            "message": "Insufficient historical trading data for technical analysis.",
            "data_source": source,
            "is_demo": is_demo,
            "retrieved_at": datetime.utcnow().isoformat() + "Z",
        }

    # Compute technical indicators
    df_ind = compute_technical_indicators(raw_df)

    latest = df_ind.iloc[-1]
    prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest

    curr_close = float(latest["close"])
    curr_high = float(latest["high"])
    curr_low = float(latest["low"])
    curr_open = float(latest["open"])
    curr_volume = int(latest["volume"])

    # Prior day session values for pivot points
    prior_session = prev if len(df_ind) > 1 else latest
    prior_high = float(prior_session["high"])
    prior_low = float(prior_session["low"])
    prior_close = float(prior_session["close"])
    pivots = calculate_pivot_points(prior_high, prior_low, prior_close)

    # 20-day high and low for dynamic swing support & resistance
    slice_20 = df_ind.iloc[-20:] if len(df_ind) >= 20 else df_ind
    swing_high_20d = float(slice_20["high"].max())
    swing_low_20d = float(slice_20["low"].min())

    # Moving Averages
    sma_20 = round(float(latest["sma_20"]), 2) if pd.notna(latest.get("sma_20")) else None
    sma_50 = round(float(latest["sma_50"]), 2) if pd.notna(latest.get("sma_50")) else None
    sma_200 = round(float(latest["sma_200"]), 2) if pd.notna(latest.get("sma_200")) else None
    ema_12 = round(float(latest["ema_12"]), 2) if pd.notna(latest.get("ema_12")) else None
    ema_26 = round(float(latest["ema_26"]), 2) if pd.notna(latest.get("ema_26")) else None

    # RSI
    rsi_14 = round(float(latest["rsi_14"]), 2) if pd.notna(latest.get("rsi_14")) else None

    # MACD
    macd_line = round(float(latest["macd_line"]), 2) if pd.notna(latest.get("macd_line")) else None
    macd_signal = round(float(latest["macd_signal"]), 2) if pd.notna(latest.get("macd_signal")) else None
    macd_hist = round(float(latest["macd_histogram"]), 2) if pd.notna(latest.get("macd_histogram")) else None

    prev_macd = float(prev["macd_line"]) if pd.notna(prev.get("macd_line")) else None
    prev_sig = float(prev["macd_signal"]) if pd.notna(prev.get("macd_signal")) else None

    # Volatility
    hist_vol_20d = compute_historical_volatility(df_ind["close"], window=20)

    # Signal Generation Lists
    bullish_signals: List[str] = []
    bearish_signals: List[str] = []
    neutral_conflicts: List[str] = []

    # 1. Price vs Moving Averages
    if sma_50 is not None:
        diff_50 = round(((curr_close - sma_50) / sma_50) * 100.0, 2)
        if curr_close > sma_50:
            bullish_signals.append(f"Price ₹{curr_close:,.2f} is trading {abs(diff_50)}% above its 50-day SMA (₹{sma_50:,.2f}).")
        else:
            bearish_signals.append(f"Price ₹{curr_close:,.2f} is trading {abs(diff_50)}% below its 50-day SMA (₹{sma_50:,.2f}).")

    if sma_200 is not None:
        diff_200 = round(((curr_close - sma_200) / sma_200) * 100.0, 2)
        if curr_close > sma_200:
            bullish_signals.append(f"Price ₹{curr_close:,.2f} holds above the long-term 200-day SMA (₹{sma_200:,.2f}), confirming an overarching primary uptrend.")
        else:
            bearish_signals.append(f"Price ₹{curr_close:,.2f} remains below the 200-day SMA (₹{sma_200:,.2f}), indicating long-term structural weakness.")

    if sma_20 is not None and sma_50 is not None:
        if curr_close > sma_20 > sma_50:
            bullish_signals.append("Short-term moving average stacked alignment: Price > SMA 20 > SMA 50.")
        elif curr_close < sma_20 < sma_50:
            bearish_signals.append("Short-term moving average stacked breakdown: Price < SMA 20 < SMA 50.")

    # Moving Average Crosses (Golden / Death Cross)
    if sma_50 is not None and sma_200 is not None and len(df_ind) >= 2:
        prev_sma50 = prev.get("sma_50")
        prev_sma200 = prev.get("sma_200")
        if pd.notna(prev_sma50) and pd.notna(prev_sma200):
            if prev_sma50 <= prev_sma200 and sma_50 > sma_200:
                bullish_signals.append("Bullish Golden Cross active: 50-day SMA crossed above 200-day SMA.")
            elif prev_sma50 >= prev_sma200 and sma_50 < sma_200:
                bearish_signals.append("Bearish Death Cross active: 50-day SMA crossed below 200-day SMA.")

    # 2. RSI Momentum
    if rsi_14 is not None:
        if rsi_14 >= 70.0:
            bearish_signals.append(f"RSI (14) is overbought at {rsi_14}, indicating elevated buyer exhaustion risk.")
        elif rsi_14 <= 30.0:
            bullish_signals.append(f"RSI (14) is oversold at {rsi_14}, suggesting deep technical discount and potential mean reversion.")
        elif 45.0 <= rsi_14 <= 55.0:
            neutral_conflicts.append(f"RSI (14) sits at {rsi_14}, representing balanced momentum between buyers and sellers.")
        elif rsi_14 > 55.0:
            bullish_signals.append(f"RSI (14) is constructive at {rsi_14}, in positive territory above the median line.")
        else:
            bearish_signals.append(f"RSI (14) is subdued at {rsi_14}, below the median 50-mark.")

    # 3. MACD Momentum & Crossover
    if macd_line is not None and macd_signal is not None:
        if prev_macd is not None and prev_sig is not None:
            if prev_macd <= prev_sig and macd_line > macd_signal:
                bullish_signals.append(f"Fresh Bullish MACD crossover: MACD line ({macd_line}) crossed above signal line ({macd_signal}).")
            elif prev_macd >= prev_sig and macd_line < macd_signal:
                bearish_signals.append(f"Fresh Bearish MACD crossover: MACD line ({macd_line}) crossed below signal line ({macd_signal}).")

        if macd_line > macd_signal:
            bullish_signals.append(f"MACD line ({macd_line}) is above signal line ({macd_signal}) with histogram at {macd_hist}.")
        else:
            bearish_signals.append(f"MACD line ({macd_line}) is below signal line ({macd_signal}) with histogram at {macd_hist}.")

    # 4. Support & Resistance Proximity
    if curr_close >= pivots["r1"]:
        bullish_signals.append(f"Price has breached above first pivot resistance R1 (₹{pivots['r1']:,.2f}).")
    elif curr_close <= pivots["s1"]:
        bearish_signals.append(f"Price has broken below first pivot support S1 (₹{pivots['s1']:,.2f}).")
    else:
        neutral_conflicts.append(f"Price is trading within the daily pivot channel: Support S1 (₹{pivots['s1']:,.2f}) to Resistance R1 (₹{pivots['r1']:,.2f}).")

    # Conflict detection
    if bullish_signals and bearish_signals:
        if len(bullish_signals) >= 2 and len(bearish_signals) >= 2:
            neutral_conflicts.append("Technical divergence observed: Long-term and short-term indicators show opposing directional signals.")

    # Overall algorithmic sentiment classification
    bullish_count = len(bullish_signals)
    bearish_count = len(bearish_signals)

    if bullish_count >= bearish_count + 2:
        overall_sentiment = "BULLISH"
    elif bearish_count >= bullish_count + 2:
        overall_sentiment = "BEARISH"
    elif abs(bullish_count - bearish_count) <= 1 and (bullish_count > 0 or bearish_count > 0):
        overall_sentiment = "CONFLICTING" if (bullish_count >= 2 and bearish_count >= 2) else "NEUTRAL"
    else:
        overall_sentiment = "NEUTRAL"

    return {
        "symbol": norm_sym,
        "status": "AVAILABLE",
        "current_price": curr_close,
        "overall_sentiment": overall_sentiment,
        "bullish_signals": bullish_signals,
        "bearish_signals": bearish_signals,
        "neutral_conflicts": neutral_conflicts,
        "indicators": {
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "ema_12": ema_12,
            "ema_26": ema_26,
            "rsi_14": rsi_14,
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_histogram": macd_hist,
            "historical_volatility_20d_annualized": hist_vol_20d,
        },
        "support_levels": {
            "pivot": pivots["pivot"],
            "s1": pivots["s1"],
            "s2": pivots["s2"],
            "swing_low_20d": round(swing_low_20d, 2),
        },
        "resistance_levels": {
            "pivot": pivots["pivot"],
            "r1": pivots["r1"],
            "r2": pivots["r2"],
            "swing_high_20d": round(swing_high_20d, 2),
        },
        "data_horizon": f"{len(df_ind)} daily trading sessions ({period})",
        "data_source": source,
        "is_demo": is_demo,
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
    }
