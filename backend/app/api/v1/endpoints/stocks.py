from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import pandas as pd
import numpy as np

from backend.app.schemas.market import (
    StockQuote,
    StockHistory,
    OHLCVPoint,
    TechnicalIndicatorResponse,
    IndicatorPoint,
    IndicatorSummary
)
from backend.app.services.market_service import (
    get_stock_quote,
    get_stock_history_df,
    normalize_symbol
)
from backend.app.services.indicators import (
    compute_technical_indicators,
    interpret_indicators
)

router = APIRouter()


@router.get("/{symbol}", response_model=StockQuote)
def get_stock(symbol: str):
    """Fetches real-time or recent quote for an NSE/BSE stock."""
    quote = get_stock_quote(symbol)
    return quote


@router.get("/{symbol}/history", response_model=StockHistory)
def get_stock_history(
    symbol: str,
    period: str = Query("6mo", description="1mo, 3mo, 6mo, 1y, 2y, 5y"),
    interval: str = Query("1d", description="1d, 1wk, 1mo")
):
    """Fetches historical OHLCV candles for charting."""
    norm_sym = normalize_symbol(symbol)
    df, is_demo, source = get_stock_history_df(norm_sym, period=period, interval=interval)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No historical data found for {symbol}")

    points = []
    for _, row in df.iterrows():
        points.append(OHLCVPoint(
            timestamp=str(row["timestamp"]).split(" ")[0].split("T")[0],
            open=round(float(row["open"]), 2),
            high=round(float(row["high"]), 2),
            low=round(float(row["low"]), 2),
            close=round(float(row["close"]), 2),
            volume=int(row["volume"])
        ))

    return StockHistory(
        symbol=norm_sym,
        period=period,
        interval=interval,
        count=len(points),
        data=points,
        data_source=source,
        is_demo=is_demo
    )


@router.get("/{symbol}/indicators", response_model=TechnicalIndicatorResponse)
def get_stock_indicators(
    symbol: str,
    period: str = Query("1y", description="History period to compute indicators on")
):
    """Computes SMA (20, 50, 200), EMA (12, 26), Wilder RSI (14), and MACD (12, 26, 9) aligned with OHLCV dates."""
    norm_sym = normalize_symbol(symbol)
    df, is_demo, source = get_stock_history_df(norm_sym, period=period, interval="1d")

    if df.empty or len(df) < 15:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient history data to compute indicators for {symbol}"
        )

    # For accurate warm-up of longer rolling windows (e.g. SMA 200, MACD, Wilder RSI),
    # compute indicators on a 2Y historical baseline, then align to the requested period.
    try:
        full_df, _, _ = get_stock_history_df(norm_sym, period="2y", interval="1d")
        if len(full_df) > len(df):
            full_ind_df = compute_technical_indicators(full_df)
            target_dates = set(df["timestamp"].astype(str).str.split(" ").str[0].str.split("T").str[0])
            full_ind_df["date_key"] = full_ind_df["timestamp"].astype(str).str.split(" ").str[0].str.split("T").str[0]
            aligned_df = full_ind_df[full_ind_df["date_key"].isin(target_dates)].copy()
            aligned_df = aligned_df.drop_duplicates(subset=["date_key"]).sort_values("date_key").reset_index(drop=True)
            ind_df = aligned_df if len(aligned_df) >= len(df) * 0.9 else compute_technical_indicators(df)
        else:
            ind_df = compute_technical_indicators(df)
    except Exception:
        ind_df = compute_technical_indicators(df)

    summary_dict = interpret_indicators(ind_df)

    points = []
    # Return all points matching the requested history period - no arbitrary tail truncations
    for _, row in ind_df.iterrows():
        def clean_val(col_name):
            val = row.get(col_name)
            return round(float(val), 2) if pd.notna(val) else None

        points.append(IndicatorPoint(
            timestamp=str(row["timestamp"]).split(" ")[0].split("T")[0],
            close=round(float(row["close"]), 2),
            sma_20=clean_val("sma_20"),
            sma_50=clean_val("sma_50"),
            sma_200=clean_val("sma_200"),
            ema_12=clean_val("ema_12"),
            ema_26=clean_val("ema_26"),
            rsi_14=clean_val("rsi_14"),
            macd_line=clean_val("macd_line"),
            macd_signal=clean_val("macd_signal"),
            macd_histogram=clean_val("macd_histogram"),
        ))

    return TechnicalIndicatorResponse(
        symbol=norm_sym,
        summary=IndicatorSummary(**summary_dict),
        indicators=points,
        data_source=source,
        is_demo=is_demo,
        disclaimer="Experimental technical indicators for educational purposes only. Not financial advice."
    )

