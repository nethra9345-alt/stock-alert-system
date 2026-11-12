import math
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


def compute_volume_ratio(volumes: pd.Series, current_idx: int, window: int = 20) -> float:
    """
    Computes current volume / previous N-session average volume.
    Strictly excludes the current session from the historical average calculation.
    """
    if current_idx <= 0:
        return 1.0

    start_idx = max(0, current_idx - window)
    hist_slice = volumes.iloc[start_idx:current_idx]

    # Filter out invalid or NaN values
    valid_vols = hist_slice.dropna().to_numpy()
    if len(valid_vols) == 0:
        return 1.0

    avg_vol = float(np.mean(valid_vols))
    curr_vol = float(volumes.iloc[current_idx])

    if avg_vol <= 0:
        return 1.0 if curr_vol <= 0 else 5.0

    return round(curr_vol / avg_vol, 2)


def classify_volume_severity(vol_ratio: float) -> str:
    """Classifies volume spike severity into defined tiers."""
    if vol_ratio >= 5.0:
        return "EXTREME"
    elif vol_ratio >= 3.0:
        return "HIGH"
    elif vol_ratio >= 2.0:
        return "ELEVATED"
    return "NORMAL"


def classify_overall_severity(price_change_pct: float, vol_ratio: float, range_pct: float) -> str:
    """Determines combined event severity based on price move and volume intensity."""
    abs_chg = abs(price_change_pct)
    if vol_ratio >= 5.0 or abs_chg >= 8.0:
        return "EXTREME"
    elif vol_ratio >= 3.0 or abs_chg >= 5.0 or range_pct >= 6.0:
        return "HIGH"
    elif vol_ratio >= 2.0 or abs_chg >= 3.0 or range_pct >= 4.0:
        return "ELEVATED"
    return "NORMAL"


def detect_market_events_from_df(
    df: pd.DataFrame,
    symbol: str,
    company_name: Optional[str] = None,
    price_threshold_pct: float = 3.5,
    volume_ratio_threshold: float = 2.5
) -> List[Dict[str, Any]]:
    """
    Inspects historical OHLCV dataframe and identifies statistical and technical market anomalies.
    Returns list of event dictionaries ready for persistence and explanation.
    """
    if df.empty or len(df) < 2:
        return []

    # Ensure required columns exist
    for col in ["timestamp", "open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            raise ValueError(f"Missing required OHLCV column: {col}")

    # Ensure clean chronological sorting
    df_clean = df.copy().sort_values("timestamp").reset_index(drop=True)

    events: List[Dict[str, Any]] = []

    for i in range(1, len(df_clean)):
        curr = df_clean.iloc[i]
        prev = df_clean.iloc[i - 1]

        prev_close = float(prev["close"])
        if prev_close <= 0:
            continue

        curr_open = float(curr["open"])
        curr_high = float(curr["high"])
        curr_low = float(curr["low"])
        curr_close = float(curr["close"])
        curr_vol = int(curr["volume"]) if pd.notna(curr["volume"]) else 0
        date_str = str(curr["timestamp"]).split(" ")[0].split("T")[0]

        # 1. Price metrics
        price_change_pct = round(((curr_close - prev_close) / prev_close) * 100.0, 2)
        gap_pct = round(((curr_open - prev_close) / prev_close) * 100.0, 2)
        intraday_range_pct = round(((curr_high - curr_low) / prev_close) * 100.0, 2)

        # 2. Volume metrics (20-day historical window excluding current session)
        vol_ratio = compute_volume_ratio(df_clean["volume"], i, window=20)
        vol_severity = classify_volume_severity(vol_ratio)
        overall_severity = classify_overall_severity(price_change_pct, vol_ratio, intraday_range_pct)

        # 3. Rolling 20-day high and low for breakout / breakdown detection
        window_start = max(0, i - 20)
        hist_window = df_clean.iloc[window_start:i]
        hist_high_20 = float(hist_window["high"].max()) if len(hist_window) > 0 else prev_close
        hist_low_20 = float(hist_window["low"].min()) if len(hist_window) > 0 else prev_close

        # Candidate event classifications for this session
        detected_types: List[str] = []

        # A. Large Price Surge or Drop
        if price_change_pct >= price_threshold_pct:
            detected_types.append("PRICE_SURGE")
        elif price_change_pct <= -price_threshold_pct:
            detected_types.append("PRICE_DROP")

        # B. Gaps
        if gap_pct >= 2.0:
            detected_types.append("GAP_UP")
        elif gap_pct <= -2.0:
            detected_types.append("GAP_DOWN")

        # C. Volume Spike
        if vol_ratio >= volume_ratio_threshold:
            detected_types.append("VOLUME_SPIKE")

        # D. Breakout or Breakdown
        if curr_close > hist_high_20 and vol_ratio >= 1.8:
            detected_types.append("BREAKOUT")
        elif curr_close < hist_low_20 and vol_ratio >= 1.8:
            detected_types.append("BREAKDOWN")

        # E. High Volatility / Sharp Reversal
        if intraday_range_pct >= 4.0 and abs(price_change_pct) < 3.0:
            detected_types.append("HIGH_VOLATILITY")

        # Create event records for all distinct qualifying types
        for ev_type in detected_types:
            events.append({
                "symbol": symbol,
                "company_name": company_name,
                "event_date": date_str,
                "event_type": ev_type,
                "severity": overall_severity,
                "price_change_pct": price_change_pct,
                "volume_ratio": vol_ratio,
                "intraday_range_pct": intraday_range_pct,
                "open_price": curr_open,
                "high_price": curr_high,
                "low_price": curr_low,
                "close_price": curr_close,
                "volume": curr_vol,
                "explanation_summary": None,
                "explanation_detail": None,
                "sources": [],
                "is_verified": False
            })

    return events
