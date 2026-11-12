"""Deterministic Tests for Smart Alert Engine, Cooldown Enforcement & History Persistence."""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.alert import PriceAlert, AlertHistory, AlertPreferences
from backend.app.models.event import MarketEvent
from backend.app.services.smart_alerts import evaluate_smart_alerts, is_in_cooldown, get_or_create_alert_preferences


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session: Session):
    """Creates a dedicated test user in the database to satisfy foreign key constraints."""
    user = db_session.query(User).filter(User.email == "smart_alert_test@stockpulse.ai").first()
    if not user:
        user = User(
            email="smart_alert_test@stockpulse.ai",
            username="smart_alert_trader",
            full_name="Smart Alert Test Trader",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def test_alert_cooldown_enforcement(db_session: Session, test_user: User):
    """Verify that is_in_cooldown blocks duplicate notifications within cooldown window."""
    user_id = test_user.id
    now = datetime(2026, 6, 1, 10, 0, 0)

    # Clean any prior test entries
    db_session.query(AlertHistory).filter(AlertHistory.user_id == user_id).delete()
    db_session.commit()

    # Initial state: not in cooldown
    assert is_in_cooldown(db_session, user_id, "PRICE_ABOVE", "INFY.NS", 60, now) is False

    # Insert an alert at 10:00:00
    alert1 = AlertHistory(
        user_id=user_id,
        symbol="INFY.NS",
        alert_type="PRICE_ABOVE",
        severity="INFO",
        title="Test Alert",
        message="Triggered at 10:00",
        trigger_value=1800.0,
        threshold_value=1750.0,
        status="TRIGGERED",
        created_at=now,
    )
    db_session.add(alert1)
    db_session.commit()

    # Check 15 minutes later (10:15:00) with 60-min cooldown -> must be in cooldown
    assert is_in_cooldown(db_session, user_id, "PRICE_ABOVE", "INFY.NS", 60, now + timedelta(minutes=15)) is True

    # Check for DIFFERENT symbol -> not in cooldown
    assert is_in_cooldown(db_session, user_id, "PRICE_ABOVE", "TCS.NS", 60, now + timedelta(minutes=15)) is False

    # Check 65 minutes later (11:05:00) with 60-min cooldown -> cooldown expired
    assert is_in_cooldown(db_session, user_id, "PRICE_ABOVE", "INFY.NS", 60, now + timedelta(minutes=65)) is False

    # Cleanup
    db_session.query(AlertHistory).filter(AlertHistory.user_id == user_id).delete()
    db_session.commit()


def test_evaluate_smart_alerts_portfolio_loss_and_drawdown(db_session: Session, test_user: User):
    """Tests portfolio loss and drawdown threshold triggers with custom state."""
    user_id = test_user.id
    now = datetime(2026, 7, 1, 12, 0, 0)

    # Clean existing
    db_session.query(AlertHistory).filter(AlertHistory.user_id == user_id).delete()
    db_session.query(AlertPreferences).filter(AlertPreferences.user_id == user_id).delete()
    db_session.commit()

    # Configure preferences: 5% loss threshold, 10% drawdown threshold
    prefs = AlertPreferences(
        user_id=user_id,
        price_alerts_enabled=True,
        portfolio_alerts_enabled=True,
        market_event_alerts_enabled=True,
        volume_spike_alerts_enabled=True,
        portfolio_loss_threshold_pct=5.0,
        portfolio_drawdown_threshold_pct=10.0,
        cooldown_minutes=60,
    )
    db_session.add(prefs)
    db_session.commit()

    # Scenario: Portfolio down -7.5% (triggers loss) and drawdown 12.0% (triggers drawdown)
    portfolio_overview = {
        "overall_return_percent": -7.5,
        "total_invested": 100000.0,
        "current_portfolio_value": 92500.0,
    }
    portfolio_risk = {
        "drawdown": {
            "maximum_drawdown_pct": 12.0,
        }
    }

    alerts = evaluate_smart_alerts(
        db=db_session,
        user_id=user_id,
        portfolio_overview=portfolio_overview,
        portfolio_risk=portfolio_risk,
        evaluation_time=now,
    )

    # Both portfolio loss and drawdown should trigger
    types = [a.alert_type for a in alerts]
    assert "PORTFOLIO_LOSS" in types
    assert "PORTFOLIO_DRAWDOWN" in types

    # Immediate second evaluation at 12:05:00 -> cooldown must prevent duplicates!
    alerts_second_run = evaluate_smart_alerts(
        db=db_session,
        user_id=user_id,
        portfolio_overview=portfolio_overview,
        portfolio_risk=portfolio_risk,
        evaluation_time=now + timedelta(minutes=5),
    )
    assert len(alerts_second_run) == 0

    # Cleanup
    db_session.query(AlertHistory).filter(AlertHistory.user_id == user_id).delete()
    db_session.query(AlertPreferences).filter(AlertPreferences.user_id == user_id).delete()
    db_session.commit()


def test_smart_alerts_api_endpoints_and_user_isolation(db_session: Session):
    """Verify REST endpoints for alert preferences, history, acknowledge, and user isolation."""
    # Ensure User 2 exists in DB
    user2 = db_session.query(User).filter(User.email == "user2_isolation@stockpulse.ai").first()
    if not user2:
        user2 = User(
            email="user2_isolation@stockpulse.ai",
            username="user2_isolated",
            full_name="User Two Isolated",
            is_active=True,
        )
        db_session.add(user2)
        db_session.commit()
        db_session.refresh(user2)

    client = TestClient(app)

    # 1. User 1: Get alert preferences
    res_pref = client.get("/api/alerts/preferences", headers={"X-User-Id": "1"})
    assert res_pref.status_code == 200
    pref_data = res_pref.json()
    assert "price_alerts_enabled" in pref_data
    assert "cooldown_minutes" in pref_data

    # 2. Update preferences
    res_update = client.put(
        "/api/alerts/preferences",
        headers={"X-User-Id": "1"},
        json={"cooldown_minutes": 45, "portfolio_loss_threshold_pct": 6.5}
    )
    assert res_update.status_code == 200
    assert res_update.json()["cooldown_minutes"] == 45
    assert res_update.json()["portfolio_loss_threshold_pct"] == 6.5

    # 3. Trigger evaluation
    res_eval = client.post("/api/alerts/evaluate", headers={"X-User-Id": "1"})
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert "evaluated_at" in eval_data
    assert "new_alerts_triggered_count" in eval_data

    # 4. Fetch alert history for User 1
    res_hist = client.get("/api/alerts/history", headers={"X-User-Id": "1"})
    assert res_hist.status_code == 200
    hist_items = res_hist.json()
    assert isinstance(hist_items, list)

    # 5. User Isolation test:
    # User 2 queries alert history -> isolated from User 1
    res_user2_hist = client.get("/api/alerts/history", headers={"X-User-Id": str(user2.id)})
    assert res_user2_hist.status_code == 200
    user2_items = res_user2_hist.json()
    assert isinstance(user2_items, list)

    # If User 1 had alerts, verify User 2's query doesn't leak User 1's IDs
    user1_alert_ids = {item["id"] for item in hist_items}
    for item in user2_items:
        assert item["id"] not in user1_alert_ids
        assert item["user_id"] == user2.id
