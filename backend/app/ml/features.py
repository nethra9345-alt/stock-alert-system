import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Any

from backend.app.services.indicators import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_macd
)

MIN_REQUIRED_BARS = 70

FEATURE_COLUMNS = [
    "sma_20_ratio",
    "sma_50_ratio",
    "ema_12_ratio",
    "ema_26_ratio",
    "rsi_14",
    "macd_line_norm",
    "macd_signal_norm",
    "macd_hist_norm",
    "return_1d",
    "return_5d",
    "volatility_10",
    "volatility_30",
    "high_low_spread",
    "close_open_ratio",
    "volume_change"
]


class InsufficientDataError(ValueError):
    """Raised when historical data is insufficient for ML feature computation and validation."""
    pass


def prepare_features(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.DataFrame]:
    """
    Transforms raw OHLCV DataFrame into stationary, leakage-free technical features.
    
    Returns:
        X (pd.DataFrame): Training feature matrix for rows where next-day target is known.
        y (pd.Series): Next-day closing price target.
        latest_features (pd.DataFrame): 1-row feature vector for today's close to predict tomorrow.
        full_df (pd.DataFrame): Complete engineered dataframe with timestamps and current prices.
    """
    if len(df_raw) < MIN_REQUIRED_BARS:
        raise InsufficientDataError(
            f"Insufficient historical data: received {len(df_raw)} candles, minimum required is {MIN_REQUIRED_BARS}."
        )

    df = df_raw.copy()

    # Sort strictly chronologically ascending
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

    close = df["close"].astype(float)
    open_p = df["open"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float)

    # 1. Moving Average Ratios (Stationary normalized price relative to trend)
    sma_20 = calculate_sma(close, 20)
    sma_50 = calculate_sma(close, 50)
    ema_12 = calculate_ema(close, 12)
    ema_26 = calculate_ema(close, 26)

    df["sma_20_ratio"] = close / sma_20
    df["sma_50_ratio"] = close / sma_50
    df["ema_12_ratio"] = close / ema_12
    df["ema_26_ratio"] = close / ema_26

    # 2. RSI (14)
    df["rsi_14"] = calculate_rsi(close, 14)

    # 3. MACD Normalized by price (stationary)
    macd_res = calculate_macd(close, 12, 26, 9)
    df["macd_line_norm"] = (macd_res["macd_line"] / close) * 100.0
    df["macd_signal_norm"] = (macd_res["signal_line"] / close) * 100.0
    df["macd_hist_norm"] = (macd_res["histogram"] / close) * 100.0

    # 4. Returns & Volatility
    df["return_1d"] = close.pct_change(1)
    df["return_5d"] = close.pct_change(5)
    df["volatility_10"] = df["return_1d"].rolling(window=10).std()
    df["volatility_30"] = df["return_1d"].rolling(window=30).std()

    # 5. Price spreads and volume dynamics
    df["high_low_spread"] = (high - low) / close
    df["close_open_ratio"] = (close - open_p) / open_p
    df["volume_change"] = volume.pct_change(1).clip(lower=-0.9, upper=5.0).fillna(0.0)

    # 6. Target definition: Next day's closing price
    # CRITICAL LEAKAGE SAFEGUARD: shift(-1) moves tomorrow's price to today's target row.
    # Row t contains features computed up to time t, and target is price at time t+1.
    df["target_next_close"] = close.shift(-1)

    # The latest row contains current day's features where tomorrow's price is not yet known.
    latest_features = df.iloc[[-1]][FEATURE_COLUMNS].copy()

    # Filter out warmup NaNs and the last row (where target is NaN) for model training
    clean_mask = df[FEATURE_COLUMNS + ["target_next_close"]].notna().all(axis=1)
    trainable_df = df[clean_mask].copy().reset_index(drop=True)

    if len(trainable_df) < 30:
        raise InsufficientDataError("Insufficient valid rows remaining after indicator warmup window.")

    X = trainable_df[FEATURE_COLUMNS].copy()
    y = trainable_df["target_next_close"].copy()

    return X, y, latest_features, trainable_df

