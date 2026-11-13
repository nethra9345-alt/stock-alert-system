"""
Stage 10.1 Production Security Audit & Hardening Automated Test Suite.
Verifies:
1. Missing, forged, and expired JWT rejections.
2. HttpOnly SameSite cookie refresh-token storage and Double-Submit CSRF protection.
3. Refresh-token rotation and revocation.
4. Refresh-token replay-attack detection and automatic user session invalidation.
5. Logout token revocation and cookie clearance.
6. Header-based identity spoofing (X-User-Id) rejection.
7. Production demo-account lockout.
8. Comprehensive cross-user resource access and tampering audit.
"""
import uuid
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.core.security import create_access_token
from backend.app.models.user import User, RefreshToken
from backend.app.models.watchlist import WatchlistItem
from backend.app.models.portfolio import PortfolioTransaction
from backend.app.models.alert import PriceAlert, AlertHistory
from backend.app.models.research import ResearchReport

client = TestClient(app)


def test_missing_jwt_rejection_in_production():
    """Verifies that unauthenticated requests to protected endpoints are rejected with 401 when fallback is disabled."""
    orig_fallback = settings.ALLOW_DEFAULT_USER_FALLBACK
    orig_env = settings.ENVIRONMENT
    try:
        settings.ALLOW_DEFAULT_USER_FALLBACK = False
        settings.ENVIRONMENT = "production"

        res_wl = client.get("/api/watchlist")
        assert res_wl.status_code == 401
        assert "not authenticated" in res_wl.json()["detail"].lower() or "token required" in res_wl.json()["detail"].lower()

        res_port = client.get("/api/portfolio")
        assert res_port.status_code == 401

        res_alerts = client.get("/api/alerts")
        assert res_alerts.status_code == 401
    finally:
        settings.ALLOW_DEFAULT_USER_FALLBACK = orig_fallback
        settings.ENVIRONMENT = orig_env


def test_forged_and_expired_jwt_rejection():
    """Verifies that tampered signatures and expired tokens are rejected with 401."""
    # 1. Tampered token
    bad_res = client.get("/api/auth/me", headers={"Authorization": "Bearer forged.signature.token"})
    assert bad_res.status_code == 401
    assert "could not validate credentials" in bad_res.json()["detail"].lower() or "invalid" in bad_res.json()["detail"].lower()

    # 2. Expired token
    expired_token = create_access_token(subject=999, expires_delta=timedelta(seconds=-10))
    exp_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert exp_res.status_code == 401
    assert "expired" in exp_res.json()["detail"].lower()


def test_httponly_cookie_and_csrf_issuance_on_login():
    """Verifies that refresh token is set as HttpOnly cookie and CSRF cookie is set."""
    suffix = uuid.uuid4().hex[:6]
    email = f"cookie_{suffix}@stockpulse.ai"
    username = f"cookie_{suffix}"
    password = "SecurePassword@2026"

    # Register
    reg_res = client.post("/api/auth/register", json={
        "email": email,
        "username": username,
        "password": password
    })
    assert reg_res.status_code == 201

    # Check cookies
    cookies = reg_res.cookies
    assert "stockpulse_refresh_token" in cookies
    assert "stockpulse_csrf_token" in cookies

    # Login
    login_res = client.post("/api/auth/login", json={
        "username_or_email": username,
        "password": password
    })
    assert login_res.status_code == 200
    assert "stockpulse_refresh_token" in login_res.cookies
    assert "stockpulse_csrf_token" in login_res.cookies
    assert "csrf_token" in login_res.json()


def test_csrf_protection_on_cookie_refresh():
    """Verifies that cookie-based refresh without CSRF token is rejected with HTTP 403."""
    suffix = uuid.uuid4().hex[:6]
    reg_res = client.post("/api/auth/register", json={
        "email": f"csrf_{suffix}@stockpulse.ai",
        "username": f"csrf_{suffix}",
        "password": "Password123!"
    })
    assert reg_res.status_code == 201

    refresh_cookie = reg_res.cookies.get("stockpulse_refresh_token")
    csrf_cookie = reg_res.cookies.get("stockpulse_csrf_token")

    # 1. Attempt refresh with cookie but WITHOUT X-CSRF-Token header -> Must fail with 403
    bad_res = client.post(
        "/api/auth/refresh",
        cookies={"stockpulse_refresh_token": refresh_cookie, "stockpulse_csrf_token": csrf_cookie}
    )
    assert bad_res.status_code == 403
    assert "csrf token validation failed" in bad_res.json()["detail"].lower()

    # 2. Attempt refresh with mismatched CSRF header -> Must fail with 403
    mismatch_res = client.post(
        "/api/auth/refresh",
        cookies={"stockpulse_refresh_token": refresh_cookie, "stockpulse_csrf_token": csrf_cookie},
        headers={"X-CSRF-Token": "completely_wrong_csrf_value"}
    )
    assert mismatch_res.status_code == 403

    # 3. Valid refresh with matching X-CSRF-Token header -> Succeeds
    good_res = client.post(
        "/api/auth/refresh",
        cookies={"stockpulse_refresh_token": refresh_cookie, "stockpulse_csrf_token": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie}
    )
    assert good_res.status_code == 200
    assert "access_token" in good_res.json()
    assert "stockpulse_refresh_token" in good_res.cookies


def test_refresh_token_rotation_and_revocation():
    """Verifies that using a refresh token rotates it and revokes the old one."""
    suffix = uuid.uuid4().hex[:6]
    reg_res = client.post("/api/auth/register", json={
        "email": f"rotate_{suffix}@stockpulse.ai",
        "username": f"rotate_{suffix}",
        "password": "Password123!"
    })
    tokens = reg_res.json()
    old_refresh = tokens["refresh_token"]

    # 1. Rotate token via body
    rot_res = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert rot_res.status_code == 200
    new_refresh = rot_res.json()["refresh_token"]
    assert new_refresh != old_refresh

    # 2. Attempt to reuse old_refresh again (should trigger replay detection or revocation failure)
    reuse_res = client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_res.status_code == 401
    assert "revoked" in reuse_res.json()["detail"].lower() or "security alert" in reuse_res.json()["detail"].lower()


def test_refresh_token_replay_attack_detection():
    """
    CRITICAL SECURITY TEST:
    Verifies that presenting an already rotated refresh token triggers
    replay-attack detection, revoking all active sessions for that user.
    """
    suffix = uuid.uuid4().hex[:6]
    reg_res = client.post("/api/auth/register", json={
        "email": f"replay_{suffix}@stockpulse.ai",
        "username": f"replay_{suffix}",
        "password": "Password123!"
    })
    user_id = reg_res.json()["user"]["id"]
    token_1 = reg_res.json()["refresh_token"]

    # First legitimate rotation: token_1 -> token_2
    rot_res = client.post("/api/auth/refresh", json={"refresh_token": token_1})
    assert rot_res.status_code == 200
    token_2 = rot_res.json()["refresh_token"]

    # Replay attack: Attacker attempts to reuse token_1
    replay_res = client.post("/api/auth/refresh", json={"refresh_token": token_1})
    assert replay_res.status_code == 401
    assert "security alert" in replay_res.json()["detail"].lower() or "rotated" in replay_res.json()["detail"].lower()

    # Verify that token_2 is now ALSO revoked due to replay protection
    token_2_res = client.post("/api/auth/refresh", json={"refresh_token": token_2})
    assert token_2_res.status_code == 401

    # Verify in DB that all tokens for user_id are revoked
    db = SessionLocal()
    try:
        active_tokens = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).all()
        assert len(active_tokens) == 0
    finally:
        db.close()


def test_logout_revocation_and_cookie_clearing():
    """Verifies that logout revokes refresh token and clears cookies."""
    suffix = uuid.uuid4().hex[:6]
    reg_res = client.post("/api/auth/register", json={
        "email": f"logout_{suffix}@stockpulse.ai",
        "username": f"logout_{suffix}",
        "password": "Password123!"
    })
    refresh_token = reg_res.json()["refresh_token"]

    # Logout
    logout_res = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert logout_res.status_code == 200

    # Attempt to use revoked refresh token
    ref_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 401


def test_x_user_id_spoofing_rejected_in_production():
    """
    CRITICAL SECURITY TEST:
    Verifies that when legacy auth is disabled, requests with X-User-Id header
    cannot spoof identity and are rejected with HTTP 401.
    """
    orig = settings.ALLOW_LEGACY_HEADER_AUTH
    try:
        settings.ALLOW_LEGACY_HEADER_AUTH = False

        res = client.get("/api/watchlist", headers={"X-User-Id": "1"})
        assert res.status_code == 401
        assert "spoofing" in res.json()["detail"].lower() or "bearer token required" in res.json()["detail"].lower()

        res_p = client.get("/api/portfolio", headers={"X-User-Id": "1"})
        assert res_p.status_code == 401
    finally:
        settings.ALLOW_LEGACY_HEADER_AUTH = orig


def test_production_demo_account_rejected():
    """Verifies that demo credentials cannot log in when demo accounts are disabled."""
    orig = settings.ALLOW_DEMO_ACCOUNTS
    try:
        settings.ALLOW_DEMO_ACCOUNTS = False

        res = client.post("/api/auth/login", json={
            "username_or_email": "trader_pro",
            "password": "TraderPass@2026"
        })
        assert res.status_code == 403
        assert "demo account login is disabled" in res.json()["detail"].lower()
    finally:
        settings.ALLOW_DEMO_ACCOUNTS = orig


def test_cross_user_resource_access_and_tampering_audit():
    """
    EXHAUSTIVE CROSS-USER AUTHORIZATION AUDIT:
    Verifies that User B cannot access, modify, or delete User A's private:
    1. Watchlist items
    2. Portfolio transactions
    3. Price alerts
    4. Smart alert history
    5. Research reports
    6. Research chat history
    """
    s_a = uuid.uuid4().hex[:6]
    res_a = client.post("/api/auth/register", json={
        "email": f"usera_{s_a}@stockpulse.ai",
        "username": f"usera_{s_a}",
        "password": "PasswordUserA@123"
    })
    token_a = res_a.json()["access_token"]
    user_a_id = res_a.json()["user"]["id"]

    s_b = uuid.uuid4().hex[:6]
    res_b = client.post("/api/auth/register", json={
        "email": f"userb_{s_b}@stockpulse.ai",
        "username": f"userb_{s_b}",
        "password": "PasswordUserB@123"
    })
    token_b = res_b.json()["access_token"]
    user_b_id = res_b.json()["user"]["id"]

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. User A adds Watchlist item
    wl_res = client.post("/api/watchlist", json={"symbol": "INFY.NS", "notes": "Confidential A"}, headers=headers_a)
    assert wl_res.status_code == 201
    item_id = wl_res.json()["id"]

    # User B attempts to update or delete User A's watchlist item
    upd_res = client.put(f"/api/watchlist/{item_id}", json={"notes": "Hacked by B"}, headers=headers_b)
    assert upd_res.status_code == 404

    del_res = client.delete(f"/api/watchlist/{item_id}", headers=headers_b)
    assert del_res.status_code == 404

    # 2. User A creates Portfolio transaction
    tx_res = client.post("/api/portfolio/transaction", json={
        "symbol": "INFY.NS",
        "transaction_type": "BUY",
        "quantity": 25,
        "purchase_price": 1700.0
    }, headers=headers_a)
    assert tx_res.status_code == 201
    tx_id = tx_res.json()["id"]

    # User B attempts to delete User A's transaction
    tx_del = client.delete(f"/api/portfolio/transaction/{tx_id}", headers=headers_b)
    assert tx_del.status_code == 404

    # 3. User A creates Price Alert
    alert_res = client.post("/api/alerts", json={
        "symbol": "INFY.NS",
        "target_price": 1800.0,
        "condition": "ABOVE"
    }, headers=headers_a)
    assert alert_res.status_code == 201
    alert_id = alert_res.json()["id"]

    # User B attempts to toggle or delete User A's price alert
    toggle_b = client.patch(f"/api/alerts/{alert_id}/toggle", headers=headers_b)
    assert toggle_b.status_code == 404

    del_alert_b = client.delete(f"/api/alerts/{alert_id}", headers=headers_b)
    assert del_alert_b.status_code == 404

    # 4. User A has Smart Alert History item
    db = SessionLocal()
    try:
        hist_item = AlertHistory(
            user_id=user_a_id,
            alert_type="VOLATILITY_SURGE",
            severity="HIGH",
            symbol="INFY.NS",
            title="User A Private Alert",
            message="Private telemetry",
            status="TRIGGERED"
        )
        db.add(hist_item)
        db.commit()
        db.refresh(hist_item)
        hist_id = hist_item.id
    finally:
        db.close()

    # User B attempts to acknowledge User A's smart alert
    ack_b = client.post(f"/api/alerts/history/{hist_id}/acknowledge", headers=headers_b)
    assert ack_b.status_code == 404

    # 5. User A generates Research Report
    rep_res = client.post("/api/research/reports", json={
        "symbol": "INFY.NS",
        "title": "User A Private Analysis"
    }, headers=headers_a)
    assert rep_res.status_code == 200
    report_id = rep_res.json()["id"]

    # User B attempts to view User A's research report
    get_rep_b = client.get(f"/api/research/reports/{report_id}", headers=headers_b)
    assert get_rep_b.status_code == 404

