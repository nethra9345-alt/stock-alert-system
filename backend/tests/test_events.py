import pytest
import datetime
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.event import MarketEvent
from backend.app.services.event_detection import (
    compute_volume_ratio,
    classify_volume_severity,
    classify_overall_severity,
    detect_market_events_from_df
)
from backend.app.services.event_explainer import (
    parse_yfinance_news_item,
    generate_event_explanation
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_volume_ratio_excludes_current_session():
    """Verify that current session volume is strictly excluded from the 20-day average."""
    # 20 historical sessions with volume 1,000,000 each
    vols = pd.Series([1000000] * 20 + [5000000])  # index 20 has volume 5M
    ratio = compute_volume_ratio(vols, current_idx=20, window=20)

    # Historical average of indices 0..19 is 1,000,000
    # Ratio = 5,000,000 / 1,000,000 = 5.0
    assert ratio == 5.0


def test_volume_severity_classification():
    assert classify_volume_severity(1.5) == "NORMAL"
    assert classify_volume_severity(2.2) == "ELEVATED"
    assert classify_volume_severity(3.8) == "HIGH"
    assert classify_volume_severity(5.5) == "EXTREME"


def test_zero_or_missing_volume_handling():
    """Verify volume calculation does not crash with zero historical volume."""
    vols = pd.Series([0, 0, 0, 0, 100000])
    ratio = compute_volume_ratio(vols, current_idx=4, window=20)
    assert ratio >= 1.0


def test_detect_market_events_normal_movements():
    """Verify no abnormal events are flagged during calm market trading."""
    dates = pd.date_range("2026-01-01", periods=25)
    # Steady 0.2% daily moves
    closes = [100.0 * (1.002 ** i) for i in range(25)]
    df = pd.DataFrame({
        "timestamp": dates.strftime("%Y-%m-%d"),
        "open": closes,
        "high": [c * 1.005 for c in closes],
        "low": [c * 0.995 for c in closes],
        "close": closes,
        "volume": [1000000] * 25
    })

    events = detect_market_events_from_df(df, "TEST.NS", "Test Corp", price_threshold_pct=3.5, volume_ratio_threshold=2.5)
    assert len(events) == 0


def test_detect_price_surge_and_volume_spike():
    """Verify detection of price surge and volume spike."""
    dates = pd.date_range("2026-01-01", periods=25)
    closes = [100.0] * 24 + [112.0]  # +12% surge on day 24
    opens = [100.0] * 24 + [106.0]   # +6% gap-up on day 24
    highs = [101.0] * 24 + [112.0]
    lows = [99.0] * 24 + [105.0]
    volumes = [1000000] * 24 + [6000000]  # 6x volume spike

    df = pd.DataFrame({
        "timestamp": dates.strftime("%Y-%m-%d"),
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })

    events = detect_market_events_from_df(df, "SURGE.NS", "Surge Corp", price_threshold_pct=3.5, volume_ratio_threshold=2.5)
    event_types = [e["event_type"] for e in events]

    assert "PRICE_SURGE" in event_types
    assert "GAP_UP" in event_types
    assert "VOLUME_SPIKE" in event_types
    assert "BREAKOUT" in event_types

    surge_event = next(e for e in events if e["event_type"] == "PRICE_SURGE")
    assert surge_event["price_change_pct"] == 12.0
    assert surge_event["volume_ratio"] == 6.0
    assert surge_event["severity"] == "EXTREME"


def test_detect_price_drop_and_gap_down():
    """Verify detection of price drop and gap-down."""
    dates = pd.date_range("2026-01-01", periods=25)
    closes = [100.0] * 24 + [91.0]   # -9% drop on day 24
    opens = [100.0] * 24 + [94.0]    # -6% gap-down
    highs = [101.0] * 24 + [95.0]
    lows = [99.0] * 24 + [90.0]
    volumes = [1000000] * 24 + [3500000]

    df = pd.DataFrame({
        "timestamp": dates.strftime("%Y-%m-%d"),
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })

    events = detect_market_events_from_df(df, "DROP.NS", "Drop Corp", price_threshold_pct=3.5, volume_ratio_threshold=2.5)
    event_types = [e["event_type"] for e in events]

    assert "PRICE_DROP" in event_types
    assert "GAP_DOWN" in event_types
    assert "VOLUME_SPIKE" in event_types
    assert "BREAKDOWN" in event_types


def test_unverified_explanation_fallback():
    """Verify that events without verified news return clear unverified notices."""
    event_payload = {
        "symbol": "UNVERIFIED.NS",
        "event_date": "2020-01-01",  # Old date with no contemporary news
        "event_type": "PRICE_SURGE",
        "price_change_pct": 5.4,
        "volume_ratio": 2.8,
        "close_price": 1500.0
    }

    result = generate_event_explanation(event_payload)
    assert result["is_verified"] is False
    assert result["sources"] == []
    assert "No verified corporate disclosure" in result["explanation_detail"]


def test_duplicate_event_prevention_in_db():
    """Verify unique constraint prevents duplicate records for same symbol, date and type."""
    db = SessionLocal()
    try:
        # Clean any prior test record
        db.query(MarketEvent).filter(MarketEvent.symbol == "DUPE_TEST.NS").delete()
        db.commit()

        ev1 = MarketEvent(
            symbol="DUPE_TEST.NS",
            company_name="Duplicate Test Corp",
            event_date="2026-11-02",
            event_type="PRICE_SURGE",
            severity="HIGH",
            price_change_pct=6.5,
            volume_ratio=3.2,
            intraday_range_pct=5.0,
            open_price=100.0,
            high_price=107.0,
            low_price=99.0,
            close_price=106.5,
            volume=5000000,
            explanation_summary="First insertion",
            is_verified=False
        )
        db.add(ev1)
        db.commit()

        # Second insertion with same symbol, event_type, event_date should violate unique constraint
        ev2 = MarketEvent(
            symbol="DUPE_TEST.NS",
            company_name="Duplicate Test Corp",
            event_date="2026-11-02",
            event_type="PRICE_SURGE",
            severity="HIGH",
            price_change_pct=6.5,
            volume_ratio=3.2,
            intraday_range_pct=5.0,
            open_price=100.0,
            high_price=107.0,
            low_price=99.0,
            close_price=106.5,
            volume=5000000,
            explanation_summary="Duplicate insertion",
            is_verified=False
        )
        db.add(ev2)
        with pytest.raises(Exception):
            db.commit()
        db.rollback()
    finally:
        db.query(MarketEvent).filter(MarketEvent.symbol == "DUPE_TEST.NS").delete()
        db.commit()
        db.close()


def test_events_api_endpoints():
    """Verify API endpoints for events: list, by symbol, and analyze."""
    # 1. Trigger analyze on RELIANCE.NS
    analyze_res = client.post("/api/events/RELIANCE.NS/analyze", json={"period": "6mo"})
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["symbol"] == "RELIANCE.NS"
    assert "detected_events_count" in data
    assert "events" in data
    assert isinstance(data["events"], list)

    # 2. Get events list
    list_res = client.get("/api/events?symbol=RELIANCE.NS")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert "count" in list_data
    assert len(list_data["events"]) >= 1

    # 3. Get single symbol events
    sym_res = client.get("/api/events/RELIANCE.NS")
    assert sym_res.status_code == 200
    assert len(sym_res.json()["events"]) >= 1

    # 4. Get latest event
    latest_res = client.get("/api/events/RELIANCE.NS/latest")
    assert latest_res.status_code == 200
    latest = latest_res.json()
    assert latest["symbol"] == "RELIANCE.NS"
    assert "event_type" in latest
    assert "severity" in latest
    assert "explanation_summary" in latest

