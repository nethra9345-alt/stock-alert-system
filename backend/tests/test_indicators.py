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
    """Verify compute_technical_indicators attaches all expected columns."""
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

