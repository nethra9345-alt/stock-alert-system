"""Deterministic Unit and Integration Tests for Portfolio Financial Analytics & Risk Engine."""

import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import math

from backend.app.models.portfolio import PortfolioTransaction
from backend.app.services.portfolio_analytics import compute_fifo_portfolio_holdings
from backend.app.services.portfolio_risk import calculate_portfolio_risk, RISK_THRESHOLDS
from fastapi.testclient import TestClient
from backend.app.main import app


class DummyTx:
    """Helper to mock PortfolioTransaction objects for isolated unit tests."""
    def __init__(self, symbol, transaction_type, quantity, purchase_price, transaction_date=None, id=None):
        self.id = id or 1
        self.symbol = symbol
        self.company_name = f"{symbol} Corp"
        self.exchange = "NSE"
        self.transaction_type = transaction_type
        self.quantity = float(quantity)
        self.purchase_price = float(purchase_price)
        self.transaction_date = transaction_date or datetime(2026, 1, 1)


def test_multiple_buy_and_partial_sell_fifo_pnl():
    """
    Test FIFO matching:
    1. BUY 10 shares @ 100 on Jan 1
    2. BUY 10 shares @ 120 on Jan 5
    Total 20 shares, cost = 2200
    3. SELL 15 shares @ 150 on Jan 10
       - Consumes 10 shares from Lot 1 (cost 1000, proceeds 1500, realized +500)
       - Consumes 5 shares from Lot 2 (cost 600, proceeds 750, realized +150)
       - Total Realized P&L = +650
       - Remaining: 5 shares from Lot 2 (cost 600, avg price 120)
    4. Current price = 140
       - Current Value = 5 * 140 = 700
       - Unrealized P&L = 700 - 600 = +100
       - Total P&L = 650 (realized) + 100 (unrealized) = +750
    """
    txs = [
        DummyTx("TCS.NS", "BUY", 10, 100.0, datetime(2026, 1, 1), 1),
        DummyTx("TCS.NS", "BUY", 10, 120.0, datetime(2026, 1, 5), 2),
        DummyTx("TCS.NS", "SELL", 15, 150.0, datetime(2026, 1, 10), 3),
    ]

    quotes = {"TCS.NS": 140.0}
    result = compute_fifo_portfolio_holdings(txs, quote_price_map=quotes)

    assert result["accounting_methodology"].startswith("FIFO")
    assert result["realized_pnl"] == 650.0
    assert result["unrealized_pnl"] == 100.0
    assert result["total_pnl"] == 750.0
    assert result["total_invested"] == 600.0
    assert result["current_portfolio_value"] == 700.0
    assert result["active_holdings_count"] == 1

    holding = result["holdings"][0]
    assert holding["symbol"] == "TCS.NS"
    assert holding["total_quantity"] == 5.0
    assert holding["avg_buy_price"] == 120.0
    assert holding["current_value"] == 700.0
    assert holding["realized_pnl"] == 650.0
    assert holding["unrealized_pnl"] == 100.0


def test_portfolio_allocation_sums_to_100_percent():
    """Verify that portfolio allocation weights sum to 100% across multiple holdings."""
    txs = [
        DummyTx("RELIANCE.NS", "BUY", 10, 2000.0, id=1),
        DummyTx("INFY.NS", "BUY", 20, 1000.0, id=2),
        DummyTx("HDFCBANK.NS", "BUY", 10, 1000.0, id=3),
    ]
    # Current values:
    # RELIANCE: 10 * 2500 = 25,000 (50%)
    # INFY: 20 * 750 = 15,000 (30%)
    # HDFCBANK: 10 * 1000 = 10,000 (20%)
    # Total = 50,000
    quotes = {
        "RELIANCE.NS": 2500.0,
        "INFY.NS": 750.0,
        "HDFCBANK.NS": 1000.0,
    }

    result = compute_fifo_portfolio_holdings(txs, quote_price_map=quotes)
    allocs = result["allocations"]

    assert len(allocs) == 3
    total_weight = sum(a["weight_pct"] for a in allocs)
    assert abs(total_weight - 100.0) < 0.1

    alloc_map = {a["symbol"]: a["weight_pct"] for a in allocs}
    assert alloc_map["RELIANCE.NS"] == 50.0
    assert alloc_map["INFY.NS"] == 30.0
    assert alloc_map["HDFCBANK.NS"] == 20.0


def test_weighted_portfolio_volatility_and_drawdown():
    """
    Test that portfolio volatility is computed using weighted portfolio daily returns,
    and maximum drawdown is computed correctly from the cumulative wealth index.
    """
    dates = [f"2026-01-{i:02d}" for i in range(1, 21)]

    # Stock A: steady upward trend
    # Stock B: volatile series with a 20% drawdown in the middle
    prices_a = [100.0 * (1.01 ** i) for i in range(20)]
    prices_b = [
        100, 102, 105, 110, 115,  # Peak at 115 on day 5
        105, 95, 92, 90, 88,      # Trough at 88 on day 10 (drawdown = (88 - 115) / 115 = -23.48%)
        91, 93, 96, 100, 102,
        105, 107, 109, 110, 112
    ]

    df_a = pd.DataFrame({"timestamp": dates, "close": prices_a})
    df_b = pd.DataFrame({"timestamp": dates, "close": prices_b})

    # Portfolio 50% A, 50% B
    holdings = [
        {"symbol": "STOCK_A", "current_value": 50000.0, "total_quantity": 10},
        {"symbol": "STOCK_B", "current_value": 50000.0, "total_quantity": 10},
    ]

    history_map = {"STOCK_A": df_a, "STOCK_B": df_b}

    risk_result = calculate_portfolio_risk(
        holdings=holdings,
        custom_history_map=history_map,
    )

    assert not risk_result["is_empty"]
    assert not risk_result["insufficient_data"]

    # Volatility should be positive and finite
    vol_data = risk_result["volatility"]
    assert vol_data["annualized_portfolio_volatility_pct"] > 0
    assert len(vol_data["stock_volatilities"]) == 2

    # Stock B volatility must be higher than Stock A volatility
    stock_vols = {sv["symbol"]: sv["annualized_volatility_pct"] for sv in vol_data["stock_volatilities"]}
    assert stock_vols["STOCK_B"] > stock_vols["STOCK_A"]

    # Drawdown check: portfolio experienced drawdown because of Stock B
    dd_data = risk_result["drawdown"]
    assert dd_data["maximum_drawdown_pct"] > 5.0
    assert dd_data["classification"] in ["LOW_DRAWDOWN", "MODERATE_DRAWDOWN", "SIGNIFICANT_DRAWDOWN"]


def test_portfolio_beta_against_benchmark():
    """Verify portfolio beta against benchmark returns."""
    dates = [f"2026-02-{i:02d}" for i in range(1, 25)]

    # Benchmark returns: periodic wave
    bench_closes = [10000.0 * (1.0 + 0.01 * math.sin(i / 2.0)) for i in range(len(dates))]
    # Stock with 1.5x amplification of benchmark (Beta ~ 1.5)
    stock_closes = [100.0 * (1.0 + 0.015 * math.sin(i / 2.0)) for i in range(len(dates))]

    bench_df = pd.DataFrame({"timestamp": dates, "close": bench_closes})
    stock_df = pd.DataFrame({"timestamp": dates, "close": stock_closes})

    holdings = [{"symbol": "BETA_STOCK", "current_value": 10000.0, "total_quantity": 10}]
    history_map = {"BETA_STOCK": stock_df}

    risk_result = calculate_portfolio_risk(
        holdings=holdings,
        custom_history_map=history_map,
        custom_benchmark_df=bench_df,
    )

    assert risk_result["has_benchmark"] is True
    assert risk_result["benchmark_beta"] is not None
    assert 1.3 <= risk_result["benchmark_beta"] <= 1.7


def test_insufficient_historical_data_handling():
    """Handles single data point or missing price series without crashing."""
    df_empty = pd.DataFrame({"timestamp": ["2026-01-01"], "close": [100.0]})
    holdings = [{"symbol": "NEW_IPO", "current_value": 5000.0, "total_quantity": 10}]

    risk_result = calculate_portfolio_risk(
        holdings=holdings,
        custom_history_map={"NEW_IPO": df_empty},
    )

    assert risk_result["insufficient_data"] is True
    assert "disclaimer" in risk_result


def test_portfolio_api_endpoints_integration():
    """Integration test of /api/portfolio/analytics, /performance, /allocation, /risk."""
    client = TestClient(app)

    # 1. Analytics
    res_analytics = client.get("/api/portfolio/analytics", headers={"X-User-Id": "1"})
    assert res_analytics.status_code == 200
    analytics_data = res_analytics.json()
    assert "total_invested" in analytics_data
    assert "current_portfolio_value" in analytics_data
    assert "realized_pnl" in analytics_data
    assert "unrealized_pnl" in analytics_data
    assert "accounting_methodology" in analytics_data

    # 2. Performance
    res_perf = client.get("/api/portfolio/performance", headers={"X-User-Id": "1"})
    assert res_perf.status_code == 200
    perf_data = res_perf.json()
    assert "performance" in perf_data
    assert isinstance(perf_data["performance"], list)

    # 3. Allocation
    res_alloc = client.get("/api/portfolio/allocation", headers={"X-User-Id": "1"})
    assert res_alloc.status_code == 200
    alloc_data = res_alloc.json()
    assert "allocations" in alloc_data
    assert "total_portfolio_value" in alloc_data

    # 4. Risk
    res_risk = client.get("/api/portfolio/risk?period=3mo", headers={"X-User-Id": "1"})
    assert res_risk.status_code == 200
    risk_data = res_risk.json()
    assert "risk_score" in risk_data
    assert "concentration" in risk_data
    assert "volatility" in risk_data
    assert "drawdown" in risk_data
