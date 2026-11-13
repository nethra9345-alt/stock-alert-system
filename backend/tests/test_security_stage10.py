import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.watchlist import WatchlistItem
from backend.app.models.portfolio import PortfolioTransaction
from backend.app.models.alert import PriceAlert
from backend.app.core.security import verify_password, hash_password, create_access_token
from datetime import timedelta

client = TestClient(app)


def test_user_registration_and_jwt_issuance():
    """Verifies user registration, bcrypt password hashing, and JWT token issuance."""
    unique_suffix = uuid.uuid4().hex[:6]
    payload = {
        "email": f"trader_{unique_suffix}@stockpulse.ai",
        "username": f"trader_{unique_suffix}",
        "password": "SecureTraderPass@2026",
        "full_name": "Stage 10 Verified User"
    }

    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["username"] == payload["username"]

    # Verify password is not exposed in response
    assert "password" not in data["user"]
    assert "hashed_password" not in data["user"]

    # Verify password is stored hashed with bcrypt in PostgreSQL
    session = SessionLocal()
    try:
        db_user = session.query(User).filter(User.email == payload["email"]).first()
        assert db_user is not None
        assert db_user.hashed_password != payload["password"]
        assert verify_password(payload["password"], db_user.hashed_password) is True
    finally:
        session.close()


def test_duplicate_registration_prevention():
    """Verifies that duplicate registration by email or username returns HTTP 400."""
    unique_suffix = uuid.uuid4().hex[:6]
    payload = {
        "email": f"dup_{unique_suffix}@stockpulse.ai",
        "username": f"dup_{unique_suffix}",
        "password": "Password123!"
    }

    # First registration
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with identical email
    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


def test_secure_login_flow():
    """Verifies successful login with valid credentials and failure on invalid passwords."""
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"auth_{unique_suffix}@stockpulse.ai"
    username = f"auth_{unique_suffix}"
    password = "CorrectSecretPass@2026"

    # Register
    client.post("/api/auth/register", json={
        "email": email,
        "username": username,
        "password": password
    })

    # 1. Login with valid username
    login_res1 = client.post("/api/auth/login", json={
        "username_or_email": username,
        "password": password
    })
    assert login_res1.status_code == 200
    assert "access_token" in login_res1.json()

    # 2. Login with valid email
    login_res2 = client.post("/api/auth/login", json={
        "username_or_email": email,
        "password": password
    })
    assert login_res2.status_code == 200

    # 3. Login with incorrect password
    bad_res = client.post("/api/auth/login", json={
        "username_or_email": username,
        "password": "WrongPassword123"
    })
    assert bad_res.status_code == 401
    assert "invalid credentials" in bad_res.json()["detail"].lower()


def test_invalid_and_expired_jwt_handling():
    """Verifies that invalid or expired JWT tokens are rejected with HTTP 401."""
    # 1. Tampered / invalid token
    res1 = client.get("/api/auth/me", headers={"Authorization": "Bearer completely_bogus_token_signature"})
    assert res1.status_code == 401
    assert "invalid token" in res1.json()["detail"].lower()

    # 2. Expired token
    expired_token = create_access_token(subject=1, expires_delta=timedelta(seconds=-10))
    res2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res2.status_code == 401
    assert "expired" in res2.json()["detail"].lower()

    # 3. Malformed header (missing Bearer prefix)
    res3 = client.get("/api/auth/me", headers={"Authorization": f"Basic {expired_token}"})
    assert res3.status_code == 401


def test_refresh_token_lifecycle():
    """Verifies that valid refresh tokens issue new access tokens."""
    unique_suffix = uuid.uuid4().hex[:6]
    reg_res = client.post("/api/auth/register", json={
        "email": f"refresh_{unique_suffix}@stockpulse.ai",
        "username": f"ref_{unique_suffix}",
        "password": "SecurePassword@123"
    })
    tokens = reg_res.json()
    refresh_token = tokens["refresh_token"]

    # Exchange refresh token
    ref_res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    assert "access_token" in ref_res.json()

    # Bogus refresh token
    bad_ref = client.post("/api/auth/refresh", json={"refresh_token": "invalid_refresh_jwt"})
    assert bad_ref.status_code == 401


def test_cross_user_data_isolation_with_jwt():
    """
    CRITICAL SECURITY AUDIT TEST:
    Verifies that User A's private watchlist and portfolio cannot be accessed or seen by User B.
    """
    # 1. Register User A
    s1 = uuid.uuid4().hex[:6]
    res_a = client.post("/api/auth/register", json={
        "email": f"user_a_{s1}@stockpulse.ai",
        "username": f"user_a_{s1}",
        "password": "PasswordUserA@123"
    })
    token_a = res_a.json()["access_token"]
    user_a_id = res_a.json()["user"]["id"]

    # 2. Register User B
    s2 = uuid.uuid4().hex[:6]
    res_b = client.post("/api/auth/register", json={
        "email": f"user_b_{s2}@stockpulse.ai",
        "username": f"user_b_{s2}",
        "password": "PasswordUserB@123"
    })
    token_b = res_b.json()["access_token"]

    # 3. User A adds a stock to their watchlist
    add_res = client.post(
        "/api/watchlist",
        json={"symbol": "TATAMOTORS.NS", "notes": "User A confidential watch item"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert add_res.status_code == 201

    # 4. User B requests their watchlist
    get_b = client.get("/api/watchlist", headers={"Authorization": f"Bearer {token_b}"})
    assert get_b.status_code == 200
    b_symbols = [item["symbol"] for item in get_b.json()]

    # User B MUST NOT see User A's custom watch item
    assert "TATAMOTORS.NS" not in b_symbols


def test_security_headers_and_request_id():
    """Verifies that all responses include OWASP security headers and unique X-Request-ID."""
    res = client.get("/api/health")
    assert res.status_code == 200

    # Headers verification
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "X-Request-ID" in res.headers
    assert len(res.headers["X-Request-ID"]) > 10


def test_health_and_readiness_endpoints():
    """Verifies /api/health, /api/health/ready and /api/health/live."""
    h_res = client.get("/api/health")
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert h_data["status"] == "online"
    assert h_data["database"]["status"] == "connected"

    ready_res = client.get("/api/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"

    live_res = client.get("/api/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"
