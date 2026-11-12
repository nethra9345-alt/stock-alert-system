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
    assert "database" in data
    assert data["database"]["status"] == "connected"
    assert data["database"]["database_type"] in ["sqlite", "postgresql"]
    assert "users" in data["database"]["verified_tables"]
    assert "watchlist_items" in data["database"]["verified_tables"]
    assert "portfolio_transactions" in data["database"]["verified_tables"]
    assert "price_alerts" in data["database"]["verified_tables"]
    # Ensure no credentials leaked
    assert "password" not in str(data).lower()
    assert "secret" not in str(data).lower()


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


def test_indicator_history_date_alignment():
    """Verify indicators align exactly with history timestamps and extend to the latest date."""
    hist_res = client.get("/api/stocks/RELIANCE.NS/history?period=6mo&interval=1d")
    ind_res = client.get("/api/stocks/RELIANCE.NS/indicators?period=6mo")

    assert hist_res.status_code == 200
    assert ind_res.status_code == 200

    hist_data = hist_res.json()["data"]
    ind_data = ind_res.json()["indicators"]

    assert len(hist_data) > 0
    assert len(ind_data) > 0

    # Ensure latest history date matches latest indicator date
    latest_hist_date = hist_data[-1]["timestamp"]
    latest_ind_date = ind_data[-1]["timestamp"]
    assert latest_hist_date == latest_ind_date, (
        f"Latest history date ({latest_hist_date}) must match latest indicator date ({latest_ind_date})"
    )

    # Latest point must have SMA 20, RSI 14, and MACD populated (not stopping months early)
    latest_ind = ind_data[-1]
    assert latest_ind["sma_20"] is not None, "SMA 20 must be populated on the latest date"
    assert latest_ind["rsi_14"] is not None, "RSI 14 must be populated on the latest date"
    assert latest_ind["macd_line"] is not None, "MACD must be populated on the latest date"


def test_datasource_metadata_consistency():
    """Verify that quote metadata is never self-contradictory."""
    res = client.get("/api/stocks/RELIANCE.NS")
    assert res.status_code == 200
    data = res.json()

    # If data_source is 'cached', is_live must be False
    if data["data_source"] == "cached":
        assert data["is_live"] is False, "Cached data cannot be flagged as live"

    # If is_live is True, is_demo must be False and market must be open
    if data["is_live"]:
        assert data["is_demo"] is False, "Live data cannot be demo"
        assert data["data_source"] == "live_market"


def test_watchlist_flow():
    # 1. Fetch watchlist
    res = client.get("/api/watchlist")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)

    # 2. Add an item
    sym = "LT.NS"
    add_res = client.post("/api/watchlist", json={"symbol": sym, "notes": "Initial Test Note"})
    assert add_res.status_code in [201, 400]

    if add_res.status_code == 201:
        created_id = add_res.json()["id"]
        # 3. Update item details
        upd_res = client.put(f"/api/watchlist/{created_id}", json={"notes": "Updated Test Note"})
        assert upd_res.status_code == 200
        assert upd_res.json()["notes"] == "Updated Test Note"

        # 4. Delete item
        del_res = client.delete(f"/api/watchlist/{created_id}")
        assert del_res.status_code == 200


def test_portfolio_overview():
    response = client.get("/api/portfolio")
    assert response.status_code == 200
    data = response.json()
    assert "total_invested" in data
    assert "current_portfolio_value" in data
    assert "holdings" in data
    assert len(data["holdings"]) > 0

    # Add transaction
    tx_res = client.post("/api/portfolio/transaction", json={
        "symbol": "ITC.NS",
        "company_name": "ITC Ltd",
        "exchange": "NSE",
        "transaction_type": "BUY",
        "quantity": 100.0,
        "purchase_price": 480.0
    })
    assert tx_res.status_code == 201
    tx_id = tx_res.json()["id"]

    # Delete transaction
    del_res = client.delete(f"/api/portfolio/transaction/{tx_id}")
    assert del_res.status_code == 200


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
    assert create_res.status_code == 201
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
