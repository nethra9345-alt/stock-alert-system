import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import Base, engine

# Ensure test DB tables exist
Base.metadata.create_all(bind=engine)

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "StockPulse AI" in data["message"]
    assert data["docs"] == "/docs"


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["service"] == "StockPulse AI"
    assert data["database"] == "healthy"
    assert "indian_market" in data


def test_market_overview():
    response = client.get("/api/market/overview")
    assert response.status_code == 200
    data = response.json()
    assert "indices" in data
    assert len(data["indices"]) == 4
    assert data["market_status"] in ["OPEN", "CLOSED"]
    assert "current_time_ist" in data


def test_market_indices():
    response = client.get("/api/market/indices")
    assert response.status_code == 200
    indices = response.json()
    assert len(indices) == 4
    names = [idx["name"] for idx in indices]
    assert "NIFTY 50" in names
    assert "SENSEX" in names
    assert "BANK NIFTY" in names
    assert "INDIA VIX" in names


def test_stock_quote_reliance():
    response = client.get("/api/stocks/RELIANCE.NS")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "RELIANCE.NS"
    assert data["price"] > 0
    assert "change" in data
    assert "data_source" in data


def test_stock_quote_normalization():
    response = client.get("/api/stocks/INFY")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "INFY.NS"


def test_stock_history():
    response = client.get("/api/stocks/TCS.NS/history?period=1mo&interval=1d")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "TCS.NS"
    assert len(data["data"]) > 0
    first_point = data["data"][0]
    assert "open" in first_point
    assert "close" in first_point
    assert "volume" in first_point


def test_stock_indicators():
    response = client.get("/api/stocks/HDFCBANK.NS/indicators?period=6mo")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "HDFCBANK.NS"
    assert "summary" in data
    assert "overall_signal" in data["summary"]
    assert len(data["indicators"]) > 0
    assert "disclaimer" in data


def test_watchlist_flow():
    # 1. Fetch watchlist
    res = client.get("/api/watchlist")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)

    # 2. Add an item
    add_res = client.post("/api/watchlist", json={"symbol": "TATAMOTORS.NS", "notes": "Test Watchlist"})
    assert add_res.status_code in [200, 400]


def test_portfolio_overview():
    response = client.get("/api/portfolio")
    assert response.status_code == 200
    data = response.json()
    assert "total_invested" in data
    assert "current_portfolio_value" in data
    assert "holdings" in data
    assert len(data["holdings"]) > 0


def test_alerts_flow():
    # 1. Fetch alerts
    response = client.get("/api/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) > 0

    # 2. Create alert
    create_res = client.post("/api/alerts", json={
        "symbol": "SBIN.NS",
        "target_price": 850.0,
        "condition": "ABOVE",
        "notes": "SBI Test Alert"
    })
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["symbol"] == "SBIN.NS"
    assert created["target_price"] == 850.0
    assert created["is_active"] is True

    # 3. Toggle alert
    alert_id = created["id"]
    toggle_res = client.patch(f"/api/alerts/{alert_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is False

    # 4. Delete alert
    del_res = client.delete(f"/api/alerts/{alert_id}")
    assert del_res.status_code == 200
