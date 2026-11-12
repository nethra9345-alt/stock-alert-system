from typing import Dict, Any, List
import numpy as np
import pandas as pd


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average (SMA)."""
    return series.rolling(window=period, min_periods=period).mean()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average (EMA)."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI) using J. Welles Wilder's exact smoothing method (1978).
    Initial average at day `period` is the simple arithmetic mean of the first `period` gains/losses.
    Subsequent averages use Wilder's recursive smoothing:
      AvgGain(t) = (AvgGain(t-1) * (period - 1) + Gain(t)) / period
      AvgLoss(t) = (AvgLoss(t-1) * (period - 1) + Loss(t)) / period
    RS = AvgGain / AvgLoss
    RSI = 100 - (100 / (1 + RS))
    Strictly bounded in [0, 100] with full edge-case handling for zero losses and zero gains.
    """
    delta = series.diff().to_numpy()
    n = len(series)
    rsi_vals = np.full(n, np.nan, dtype=float)
    if n <= period:
        return pd.Series(rsi_vals, index=series.index)

    gains = np.maximum(delta, 0.0)
    losses = np.maximum(-delta, 0.0)

    # Initial average at index = period using simple arithmetic mean
    avg_gain = float(np.mean(gains[1:period + 1]))
    avg_loss = float(np.mean(losses[1:period + 1]))

    if avg_loss == 0.0:
        rsi_vals[period] = 100.0 if avg_gain > 0 else 50.0
    elif avg_gain == 0.0:
        rsi_vals[period] = 0.0
    else:
        rs = avg_gain / avg_loss
        rsi_vals[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0.0:
            rsi_vals[i] = 100.0 if avg_gain > 0 else 50.0
        elif avg_gain == 0.0:
            rsi_vals[i] = 0.0
        else:
            rs = avg_gain / avg_loss
            rsi_vals[i] = 100.0 - (100.0 / (1.0 + rs))

    return pd.Series(rsi_vals, index=series.index)


def calculate_macd(
    series: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict[str, pd.Series]:
    """
    Calculate Moving Average Convergence Divergence (MACD).
    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(signal_period) of MACD Line
    Histogram = MACD Line - Signal Line
    """
    ema_fast = calculate_ema(series, fast_period)
    ema_slow = calculate_ema(series, slow_period)

    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal_period)
    histogram = macd_line - signal_line

    return {
        "macd_line": macd_line,
        "signal_line": signal_line,
        "histogram": histogram
    }


def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes all standard indicators onto a DataFrame containing at least a 'close' column.
    Returns the dataframe with added indicator columns.
    """
    if "close" not in df.columns:
        raise ValueError("DataFrame must contain a 'close' column")

    res = df.copy()

    # Moving Averages
    res["sma_20"] = calculate_sma(res["close"], 20)
    res["sma_50"] = calculate_sma(res["close"], 50)
    res["sma_200"] = calculate_sma(res["close"], 200)

    res["ema_12"] = calculate_ema(res["close"], 12)
    res["ema_26"] = calculate_ema(res["close"], 26)

    # Momentum Indicators
    res["rsi_14"] = calculate_rsi(res["close"], 14)

    # MACD
    macd_dict = calculate_macd(res["close"], fast_period=12, slow_period=26, signal_period=9)
    res["macd_line"] = macd_dict["macd_line"]
    res["macd_signal"] = macd_dict["signal_line"]
    res["macd_histogram"] = macd_dict["histogram"]

    return res


def interpret_indicators(df_with_indicators: pd.DataFrame) -> Dict[str, Any]:
    """
    Generates a rule-based algorithmic summary of current indicators without future lookahead.
    """
    if len(df_with_indicators) == 0:
        return {
            "current_rsi": None,
            "rsi_signal": "NEUTRAL",
            "macd_signal": "NEUTRAL",
            "trend_sma": "NEUTRAL",
            "overall_signal": "NEUTRAL"
        }

    latest = df_with_indicators.iloc[-1]
    prev = df_with_indicators.iloc[-2] if len(df_with_indicators) > 1 else latest

    # RSI Interpretation
    rsi_val = float(latest["rsi_14"]) if pd.notna(latest.get("rsi_14")) else None
    if rsi_val is not None:
        if rsi_val >= 70:
            rsi_signal = "OVERBOUGHT"
        elif rsi_val <= 30:
            rsi_signal = "OVERSOLD"
        else:
            rsi_signal = "NEUTRAL"
    else:
        rsi_signal = "NEUTRAL"

    # MACD Interpretation
    macd_line = latest.get("macd_line")
    macd_signal_line = latest.get("macd_signal")
    prev_macd = prev.get("macd_line")
    prev_signal = prev.get("macd_signal")

    if pd.notna(macd_line) and pd.notna(macd_signal_line) and pd.notna(prev_macd) and pd.notna(prev_signal):
        if prev_macd <= prev_signal and macd_line > macd_signal_line:
            macd_signal = "BULLISH_CROSSOVER"
        elif prev_macd >= prev_signal and macd_line < macd_signal_line:
            macd_signal = "BEARISH_CROSSOVER"
        elif macd_line > macd_signal_line:
            macd_signal = "BULLISH"
        else:
            macd_signal = "BEARISH"
    else:
        macd_signal = "NEUTRAL"

    # SMA Trend (Price vs SMA 50 and SMA 200)
    close_val = latest["close"]
    sma_50 = latest.get("sma_50")
    sma_200 = latest.get("sma_200")

    if pd.notna(sma_50) and pd.notna(sma_200):
        if close_val > sma_50 > sma_200:
            trend_sma = "STRONG_BULLISH"
        elif close_val < sma_50 < sma_200:
            trend_sma = "STRONG_BEARISH"
        elif close_val > sma_50:
            trend_sma = "BULLISH"
        else:
            trend_sma = "BEARISH"
    elif pd.notna(sma_50):
        trend_sma = "BULLISH" if close_val > sma_50 else "BEARISH"
    else:
        trend_sma = "NEUTRAL"

    # Overall Consensus Score
    bullish_votes = 0
    bearish_votes = 0

    if rsi_signal == "OVERSOLD":
        bullish_votes += 1
    elif rsi_signal == "OVERBOUGHT":
        bearish_votes += 1

    if "BULLISH" in macd_signal:
        bullish_votes += 1
    elif "BEARISH" in macd_signal:
        bearish_votes += 1

    if "BULLISH" in trend_sma:
        bullish_votes += 1
    elif "BEARISH" in trend_sma:
        bearish_votes += 1

    if bullish_votes > bearish_votes:
        overall_signal = "BULLISH"
    elif bearish_votes > bullish_votes:
        overall_signal = "BEARISH"
    else:
        overall_signal = "NEUTRAL"

    return {
        "current_rsi": round(rsi_val, 2) if rsi_val is not None else None,
        "rsi_signal": rsi_signal,
        "macd_signal": macd_signal,
        "trend_sma": trend_sma,
        "overall_signal": overall_signal
    }

