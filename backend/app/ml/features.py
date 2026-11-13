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

ADVANCED_FEATURE_COLUMNS = [
    # Trend & Moving average ratios
    "sma_10_ratio",
    "sma_20_ratio",
    "sma_50_ratio",
    "sma_200_ratio",
    "ema_12_ratio",
    "ema_26_ratio",
    "ma_spread_20_50",
    # Momentum
    "rsi_14",
    "rsi_7",
    "macd_line_norm",
    "macd_signal_norm",
    "macd_hist_norm",
    "roc_10",
    "momentum_5d",
    # Price dynamics & returns
    "return_1d",
    "log_return_1d",
    "return_5d",
    "return_10d",
    "return_21d",
    "overnight_gap",
    "intraday_range",
    "close_open_ratio",
    # Volatility
    "volatility_10",
    "volatility_30",
    "atr_14_norm",
    "high_low_spread",
    # Volume dynamics
    "volume_change",
    "volume_ratio_20"
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


HORIZON_MAP = {
    "1d": 1,
    "5d": 5,
    "10d": 10
}


def prepare_advanced_features(
    df_raw: pd.DataFrame,
    horizon: str = "1d"
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame, pd.DataFrame, List[str]]:
    """
    Transforms raw OHLCV DataFrame into 28 stationary, leakage-free technical features,
    computing stationary percentage return targets for multi-horizon forecasting (1d, 5d, 10d).

    Returns:
        X (pd.DataFrame): Advanced feature matrix strictly computed at t <= observation.
        y_return (pd.Series): Target future percentage return over horizon h: (Close(t+h) - Close(t)) / Close(t).
        y_price (pd.Series): Target future nominal price: Close(t+h).
        latest_features (pd.DataFrame): 1-row feature vector for today to forecast future horizon.
        trainable_df (pd.DataFrame): Complete aligned dataframe with timestamps and prices.
        feature_cols (List[str]): List of active feature names.
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

    # 1. Moving Averages & Trend Ratios
    sma_10 = calculate_sma(close, 10)
    sma_20 = calculate_sma(close, 20)
    sma_50 = calculate_sma(close, 50)
    # Robust SMA 200 with fallback for shorter series
    if len(close) >= 200:
        sma_200 = calculate_sma(close, 200).fillna(sma_50)
    else:
        sma_200 = sma_50.copy()

    ema_12 = calculate_ema(close, 12)
    ema_26 = calculate_ema(close, 26)

    df["sma_10_ratio"] = close / sma_10
    df["sma_20_ratio"] = close / sma_20
    df["sma_50_ratio"] = close / sma_50
    df["sma_200_ratio"] = close / sma_200
    df["ema_12_ratio"] = close / ema_12
    df["ema_26_ratio"] = close / ema_26
    df["ma_spread_20_50"] = (sma_20 - sma_50) / close

    # 2. Momentum & Oscillators
    df["rsi_14"] = calculate_rsi(close, 14)
    df["rsi_7"] = calculate_rsi(close, 7)

    macd_res = calculate_macd(close, 12, 26, 9)
    df["macd_line_norm"] = (macd_res["macd_line"] / close) * 100.0
    df["macd_signal_norm"] = (macd_res["signal_line"] / close) * 100.0
    df["macd_hist_norm"] = (macd_res["histogram"] / close) * 100.0
    df["roc_10"] = (close - close.shift(10)) / close.shift(10) * 100.0
    df["momentum_5d"] = (close - close.shift(5)) / close.shift(5)

    # 3. Price Dynamics & Returns
    df["return_1d"] = close.pct_change(1)
    df["log_return_1d"] = np.log(close / close.shift(1))
    df["return_5d"] = close.pct_change(5)
    df["return_10d"] = close.pct_change(10)
    df["return_21d"] = close.pct_change(21)
    df["overnight_gap"] = (open_p - close.shift(1)) / close.shift(1)
    df["intraday_range"] = (high - low) / open_p
    df["close_open_ratio"] = (close - open_p) / open_p

    # 4. Volatility & Spreads
    df["volatility_10"] = df["return_1d"].rolling(window=10).std()
    df["volatility_30"] = df["return_1d"].rolling(window=30).std()
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_14 = tr.rolling(window=14).mean()
    df["atr_14_norm"] = atr_14 / close
    df["high_low_spread"] = (high - low) / close

    # 5. Volume Dynamics (Current session excluded from baseline to prevent leakage)
    df["volume_change"] = volume.pct_change(1).clip(lower=-0.9, upper=5.0).fillna(0.0)
    past_vol_avg = volume.shift(1).rolling(window=20).mean()
    df["volume_ratio_20"] = (volume / past_vol_avg).clip(lower=0.1, upper=10.0).fillna(1.0)

    # 6. Multi-Horizon Targets
    shift_steps = HORIZON_MAP.get(horizon, 1)
    # Target nominal price at t+h
    df["target_future_price"] = close.shift(-shift_steps)
    # Target stationary percentage return over horizon h
    df["target_return"] = (df["target_future_price"] - close) / close

    # Feature vector for current day to predict unseen future horizon
    latest_features = df.iloc[[-1]][ADVANCED_FEATURE_COLUMNS].copy()

    # Filter out warmup window NaNs and the last h rows where future price is not yet known
    clean_mask = df[ADVANCED_FEATURE_COLUMNS + ["target_return", "target_future_price"]].notna().all(axis=1)
    trainable_df = df[clean_mask].copy().reset_index(drop=True)

    if len(trainable_df) < 30:
        raise InsufficientDataError("Insufficient valid rows remaining after indicator warmup window.")

    X = trainable_df[ADVANCED_FEATURE_COLUMNS].copy()
    y_return = trainable_df["target_return"].copy()
    y_price = trainable_df["target_future_price"].copy()

    return X, y_return, y_price, latest_features, trainable_df, ADVANCED_FEATURE_COLUMNS


