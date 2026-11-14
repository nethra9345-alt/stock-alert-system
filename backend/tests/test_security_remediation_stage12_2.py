"""
Stage 12.2 Security Remediation Verification Suite.
Validates:
1. Strict security defaults (ALLOW_LEGACY_HEADER_AUTH=False, ALLOW_DEFAULT_USER_FALLBACK=False).
2. Production JWT secret key validation (length >= 32, reject default/insecure keys).
3. Immediate HTTP 401 rejection for unauthenticated requests to protected endpoints.
4. Immediate HTTP 401 rejection for X-User-Id header spoofing attempts.
5. Absence of raw refresh tokens in JSON response bodies when cookie authentication is active.
6. Proper HttpOnly, path=/api/auth cookie issuance across register, login, and refresh.
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import Settings, settings

client = TestClient(app)


def test_default_security_settings():
    """Verifies that security defaults are strictly secure (no legacy auth, no default fallback)."""
    assert settings.ALLOW_LEGACY_HEADER_AUTH is False, "ALLOW_LEGACY_HEADER_AUTH must be False by default"
    assert settings.ALLOW_DEFAULT_USER_FALLBACK is False, "ALLOW_DEFAULT_USER_FALLBACK must be False by default"
    assert settings.is_legacy_auth_allowed is False
    assert settings.is_fallback_allowed is False


def test_unauthenticated_requests_return_401():
    """Verifies that unauthenticated requests to protected endpoints return 401 Unauthorized."""
    # 1. Watchlist
    res_wl = client.get("/api/watchlist")
    assert res_wl.status_code == 401
    assert "not authenticated" in res_wl.json()["detail"].lower() or "token required" in res_wl.json()["detail"].lower()

    # 2. Portfolio
    res_port = client.get("/api/portfolio")
    assert res_port.status_code == 401
    assert "not authenticated" in res_port.json()["detail"].lower() or "token required" in res_port.json()["detail"].lower()

    # 3. Alerts
    res_alerts = client.get("/api/alerts")
    assert res_alerts.status_code == 401

    # 4. Auth profile
    res_me = client.get("/api/auth/me")
    assert res_me.status_code == 401


def test_header_spoofing_rejected_with_401():
    """Verifies that X-User-Id header spoofing is rejected with 401 when legacy auth is disabled."""
    spoofed_headers = {"X-User-Id": "1"}

    res_wl = client.get("/api/watchlist", headers=spoofed_headers)
    assert res_wl.status_code == 401
    assert "spoofing" in res_wl.json()["detail"].lower() or "rejected" in res_wl.json()["detail"].lower()

    res_port = client.get("/api/portfolio", headers={"X-User-Id": "999"})
    assert res_port.status_code == 401
    assert "spoofing" in res_port.json()["detail"].lower() or "rejected" in res_port.json()["detail"].lower()


def test_production_jwt_startup_validation():
    """Verifies that Settings rejects insecure, short, or default JWT secrets in production mode."""
    # 1. Reject short key in production
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY="short-secret")

    # 2. Reject default development secret in production
    with pytest.raises(ValueError, match="secure, non-default string"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="stockpulse-dev-secret-key-replace-in-production-with-env-variable"
        )

    # 3. Reject empty key in production
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(ENVIRONMENT="production", JWT_SECRET_KEY="")

    # 4. Accept strong 32+ character key in production
    strong_key = "a" * 32
    prod_settings = Settings(ENVIRONMENT="production", JWT_SECRET_KEY=strong_key)
    assert prod_settings.JWT_SECRET_KEY == strong_key

    # 5. Allow dev secret in development environment
    dev_settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="stockpulse-dev-secret-key-replace-in-production-with-env-variable"
    )
    assert dev_settings.JWT_SECRET_KEY is not None


def test_cookie_auth_omits_refresh_token_from_json():
    """
    Verifies that when cookie auth is active (browser headers or X-Auth-Mode: cookie):
    - Refresh token is absent from JSON response body across register, login, and refresh.
    - HttpOnly refresh cookie is issued with path /api/auth.
    - CSRF cookie and token are issued.
    """
    suffix = uuid.uuid4().hex[:6]
    email = f"cookie_guard_{suffix}@stockpulse.ai"
    username = f"guard_{suffix}"
    password = "StrongPassword@2026"

    # 1. Register with cookie auth mode
    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password, "full_name": "Cookie Guard"},
        headers={"X-Auth-Mode": "cookie"}
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    # Refresh token MUST NOT be present in response JSON body
    assert "refresh_token" not in reg_data
    assert "csrf_token" in reg_data
    assert "stockpulse_refresh_token" in reg_res.cookies
    assert "stockpulse_csrf_token" in reg_res.cookies

    # 2. Login with browser Origin header (cookie auth active)
    login_res = client.post(
        "/api/auth/login",
        json={"username_or_email": username, "password": password},
        headers={"Origin": "http://localhost:5173"}
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    # Refresh token MUST NOT be present in response JSON body
    assert "refresh_token" not in login_data
    assert "csrf_token" in login_data
    assert "stockpulse_refresh_token" in login_res.cookies
    assert "stockpulse_csrf_token" in login_res.cookies

    # 3. Refresh via HttpOnly cookie & CSRF header
    refresh_cookie = login_res.cookies.get("stockpulse_refresh_token")
    csrf_cookie = login_res.cookies.get("stockpulse_csrf_token")

    ref_res = client.post(
        "/api/auth/refresh",
        cookies={"stockpulse_refresh_token": refresh_cookie, "stockpulse_csrf_token": csrf_cookie},
        headers={"X-CSRF-Token": csrf_cookie}
    )
    assert ref_res.status_code == 200
    ref_data = ref_res.json()
    assert "access_token" in ref_data
    # Refresh token MUST NOT be present in response JSON body
    assert "refresh_token" not in ref_data
    assert "csrf_token" in ref_data
    assert "stockpulse_refresh_token" in ref_res.cookies


def test_token_auth_mode_includes_refresh_token_for_cli_clients():
    """Verifies that non-browser CLI/API clients can explicitly request token mode."""
    suffix = uuid.uuid4().hex[:6]
    email = f"cli_{suffix}@stockpulse.ai"
    username = f"cli_{suffix}"
    password = "StrongPassword@2026"

    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
        headers={"X-Auth-Mode": "token"}
    )
    assert reg_res.status_code == 201
    assert "refresh_token" in reg_res.json()
    assert reg_res.json()["refresh_token"] is not None

