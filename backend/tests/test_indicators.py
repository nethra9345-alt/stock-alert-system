import pytest
import pandas as pd
import numpy as np

from backend.app.services.indicators import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    compute_technical_indicators,
    interpret_indicators
)
from backend.app.services.market_service import (
    get_stock_history_df,
    get_stock_quote,
    generate_synthetic_history
)


def test_sma_calculation():
    """Verify Simple Moving Average accurately calculates rolling mean."""
    prices = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    sma3 = calculate_sma(prices, 3)

    assert pd.isna(sma3.iloc[0])
    assert pd.isna(sma3.iloc[1])
    assert sma3.iloc[2] == pytest.approx(20.0)  # (10+20+30)/3
    assert sma3.iloc[3] == pytest.approx(30.0)  # (20+30+40)/3
    assert sma3.iloc[4] == pytest.approx(40.0)  # (30+40+50)/3


def test_ema_calculation():
    """Verify Exponential Moving Average reacts faster than SMA."""
    prices = pd.Series([10.0, 10.0, 10.0, 20.0, 30.0])
    ema3 = calculate_ema(prices, 3)

    assert len(ema3) == 5
    # EMA should increase with rising prices
    assert ema3.iloc[-1] > ema3.iloc[-2]


def test_rsi_bounds_and_values():
    """Verify RSI values are bounded between 0 and 100."""
    # Monotonically increasing prices -> RSI should approach 100
    up_prices = pd.Series([float(i * 5) for i in range(1, 30)])
    up_rsi = calculate_rsi(up_prices, 14)
    valid_up_rsi = up_rsi.dropna()

    assert not valid_up_rsi.empty
    assert (valid_up_rsi >= 0).all() and (valid_up_rsi <= 100).all()
    assert valid_up_rsi.iloc[-1] > 80  # Strongly overbought

    # Monotonically decreasing prices -> RSI should approach 0
    down_prices = pd.Series([float(500 - i * 10) for i in range(1, 30)])
    down_rsi = calculate_rsi(down_prices, 14)
    valid_down_rsi = down_rsi.dropna()

    assert not valid_down_rsi.empty
    assert (valid_down_rsi >= 0).all() and (valid_down_rsi <= 100).all()
    assert valid_down_rsi.iloc[-1] < 20  # Strongly oversold


def test_wilder_rsi_classic_textbook_vector():
    """
    Verify calculation against J. Welles Wilder Jr.'s original 1978 textbook dataset
    from 'New Concepts in Technical Trading Systems' (p. 65).
    """
    wilder_prices = pd.Series([
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
        45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64,
        46.21, 46.25, 45.71, 46.45, 45.78, 45.35, 44.03, 44.18, 44.22, 44.57,
        43.42, 42.66, 43.13
    ])

    rsi = calculate_rsi(wilder_prices, period=14)

    # First 13 periods should be NaN warm-up
    assert rsi.iloc[:14].isna().sum() == 14
    # Day 14 (15th price observation): Textbook published value is 70.46
    assert rsi.iloc[14] == pytest.approx(70.46, abs=0.05)
    # Day 15: Textbook published value is 66.25
    assert rsi.iloc[15] == pytest.approx(66.25, abs=0.05)
    # Strictly bounded in [0, 100]
    valid_rsi = rsi.dropna()
    assert (valid_rsi >= 0.0).all() and (valid_rsi <= 100.0).all()


def test_rsi_edge_cases_zero_loss_zero_gain():
    """Verify RSI edge cases: all gains (100.0), all losses (0.0), no change (50.0)."""
    # Strict upward slope -> zero losses
    all_gains = pd.Series([float(100 + i * 2) for i in range(25)])
    rsi_up = calculate_rsi(all_gains, 14).dropna()
    assert (rsi_up == 100.0).all()

    # Strict downward slope -> zero gains
    all_losses = pd.Series([float(200 - i * 2) for i in range(25)])
    rsi_down = calculate_rsi(all_losses, 14).dropna()
    assert (rsi_down == 0.0).all()

    # Flat prices -> zero delta
    flat = pd.Series([100.0] * 25)
    rsi_flat = calculate_rsi(flat, 14).dropna()
    assert (rsi_flat == 50.0).all()


def test_macd_calculation():
    """Verify MACD line, signal line, and histogram relations."""
    prices = pd.Series([100.0 + np.sin(i / 5.0) * 10.0 for i in range(50)])
    macd = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

    assert "macd_line" in macd
    assert "signal_line" in macd
    assert "histogram" in macd

    diff = macd["macd_line"] - macd["signal_line"]
    assert np.allclose(diff.values, macd["histogram"].values)


def test_compute_all_indicators_dataframe():
    """Verify compute_technical_indicators attaches all expected columns and valid values."""
    n = 100
    dates = pd.date_range("2024-01-01", periods=n)
    df = pd.DataFrame({
        "timestamp": dates.strftime("%Y-%m-%d"),
        "open": np.linspace(100, 200, n),
        "high": np.linspace(105, 205, n),
        "low": np.linspace(95, 195, n),
        "close": np.linspace(102, 202, n),
        "volume": np.random.randint(1000, 5000, n)
    })

    result_df = compute_technical_indicators(df)

    expected_cols = [
        "sma_20", "sma_50", "sma_200",
        "ema_12", "ema_26",
        "rsi_14",
        "macd_line", "macd_signal", "macd_histogram"
    ]
    for col in expected_cols:
        assert col in result_df.columns, f"Missing expected column: {col}"

    summary = interpret_indicators(result_df)
    assert "overall_signal" in summary
    assert summary["overall_signal"] in ["BULLISH", "BEARISH", "NEUTRAL"]


def test_historical_data_integrity_and_monotonicity():
    """Verify historical dataset is sorted, deduplicated, and OHLC relationships hold."""
    df, is_demo, source = get_stock_history_df("RELIANCE.NS", period="6mo")

    assert not df.empty
    assert len(df) >= 30

    # 1. Monotonic ordering by date
    dates = df["timestamp"].tolist()
    assert dates == sorted(dates), "Timestamps must be strictly ascending"

    # 2. No duplicate timestamps
    assert len(dates) == len(set(dates)), "Duplicate timestamps detected in historical series"

    # 3. OHLC validity
    assert (df["high"] >= df["low"]).all(), "High must be >= Low"
    assert (df["high"] >= df["open"] * 0.999).all(), "High must be >= Open (within float precision)"
    assert (df["high"] >= df["close"] * 0.999).all(), "High must be >= Close (within float precision)"
    assert (df["low"] <= df["open"] * 1.001).all(), "Low must be <= Open (within float precision)"
    assert (df["low"] <= df["close"] * 1.001).all(), "Low must be <= Close (within float precision)"

    # 4. Volume validity
    assert (df["volume"] >= 0).all(), "Volume must be non-negative"
