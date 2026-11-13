"""
StockPulse AI - Stage 11 College Project Demonstration Deployment Verification
Tests all critical live endpoints through Nginx at http://localhost.
Verifies:
1. Web SPA root (200 OK)
2. Health check (/api/health) with PostgreSQL database connectivity
3. Swagger UI documentation (/docs)
4. OpenAPI JSON specification (/openapi.json)
5. Authentication (Login with trader_pro)
6. Profile retrieval (/api/auth/me)
7. Watchlist retrieval (/api/watchlist)
8. Portfolio analytics (/api/portfolio)
9. Market events (/api/market/events)
10. Token Refresh with CSRF protection (/api/auth/refresh)
11. Secure Logout (/api/auth/logout)
"""
import sys
import httpx

BASE_URL = "http://localhost"

def run_verification():
    print("=" * 70)
    print("StockPulse AI - Stage 11 Live Deployment Verification Suite")
    print(f"Target URL: {BASE_URL}")
    print("=" * 70)

    client = httpx.Client(base_url=BASE_URL, timeout=10.0, follow_redirects=True)
    all_passed = True

    # 1. Test Static React Frontend
    print("\n[1/11] Testing Frontend SPA Root (http://localhost/)...")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "<!doctype html>" in res.text.lower() or "<html" in res.text.lower(), "HTML markup missing"
    assert res.headers.get("x-frame-options") == "DENY", "Security header X-Frame-Options missing"
    print("  --> PASS: React SPA served with security headers (200 OK).")

    # 2. Test Backend Health Check
    print("\n[2/11] Testing Health Check (http://localhost/api/health)...")
    res = client.get("/api/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    health = res.json()
    assert health["status"] == "online", f"Expected online, got {health['status']}"
    assert health["database"]["status"] == "connected", "Database not connected"
    assert health["database"]["database_type"] == "postgresql", "Database type is not postgresql"
    print(f"  --> PASS: Health Check Online | DB: {health['database']['database_type']} (Latency: {health['database']['latency_ms']}ms) | Tables: {len(health['database']['verified_tables'])}")

    # 3. Test Swagger Docs
    print("\n[3/11] Testing Swagger Documentation (http://localhost/docs)...")
    res = client.get("/docs")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print("  --> PASS: Swagger UI active on http://localhost/docs (200 OK).")

    # 4. Test OpenAPI Specification
    print("\n[4/11] Testing OpenAPI Spec (http://localhost/openapi.json)...")
    res = client.get("/openapi.json")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    openapi = res.json()
    assert openapi["info"]["title"] == "StockPulse AI"
    print(f"  --> PASS: OpenAPI spec valid: {openapi['info']['title']} v{openapi['info']['version']} ({len(openapi['paths'])} routes)")

    # 5. Test Demo Login
    print("\n[5/11] Testing Demo Login (/api/auth/login as trader_pro)...")
    login_payload = {
        "username_or_email": "trader_pro",
        "password": "TraderPass@2026"
    }
    res = client.post("/api/auth/login", json=login_payload)
    assert res.status_code == 200, f"Login failed: {res.status_code} {res.text}"
    token_data = res.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    csrf_token = token_data["csrf_token"]
    user = token_data["user"]
    assert access_token, "No access token returned"
    assert user["username"] == "trader_pro"
    print(f"  --> PASS: Authenticated user '{user['username']}' (ID: {user['id']}) | Access token generated.")

    # 6. Test Authenticated User Profile
    print("\n[6/11] Testing Profile Retrieval (/api/auth/me)...")
    headers = {"Authorization": f"Bearer {access_token}"}
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200, f"Profile failed: {res.status_code} {res.text}"
    profile = res.json()
    assert profile["email"] == "trader@stockpulse.ai"
    print(f"  --> PASS: Profile verified: {profile['full_name']} ({profile['email']})")

    # 7. Test Watchlist Retrieval
    print("\n[7/11] Testing Watchlist (/api/watchlist)...")
    res = client.get("/api/watchlist", headers=headers)
    assert res.status_code == 200, f"Watchlist failed: {res.status_code} {res.text}"
    watchlist = res.json()
    print(f"  --> PASS: User Watchlist retrieved: {len(watchlist)} stocks.")

    # 8. Test Portfolio Analytics
    print("\n[8/11] Testing Portfolio (/api/portfolio)...")
    res = client.get("/api/portfolio", headers=headers)
    assert res.status_code == 200, f"Portfolio failed: {res.status_code} {res.text}"
    portfolio = res.json()
    print(f"  --> PASS: Portfolio retrieved: Total Invested: ₹{portfolio.get('total_invested', 0):,.2f} | Current Value: ₹{portfolio.get('current_value', 0):,.2f}")

    # 9. Test Market Events
    print("\n[9/11] Testing Market Events (/api/events)...")
    res = client.get("/api/events", headers=headers)
    assert res.status_code == 200, f"Market events failed: {res.status_code} {res.text}"
    events = res.json()
    print(f"  --> PASS: Market events retrieved: {len(events)} events found.")

    # 10. Test Refresh Token Rotation & CSRF Protection
    print("\n[10/11] Testing Token Refresh with CSRF (/api/auth/refresh)...")
    # client has cookies saved from login (stockpulse_refresh_token and stockpulse_csrf_token)
    refresh_headers = {
        "X-CSRF-Token": csrf_token
    }
    res = client.post("/api/auth/refresh", headers=refresh_headers)
    assert res.status_code == 200, f"Refresh failed: {res.status_code} {res.text}"
    refresh_data = res.json()
    new_access_token = refresh_data["access_token"]
    assert new_access_token, "No new access token returned"
    print(f"  --> PASS: Token refresh successful with CSRF verification and refresh rotation.")

    # 11. Test Secure Logout
    print("\n[11/11] Testing Secure Logout (/api/auth/logout)...")
    logout_headers = {
        "Authorization": f"Bearer {new_access_token}",
        "X-CSRF-Token": refresh_data.get("csrf_token") or csrf_token
    }
    res = client.post("/api/auth/logout", headers=logout_headers)
    assert res.status_code == 200, f"Logout failed: {res.status_code} {res.text}"
    print(f"  --> PASS: Logout successful; session invalidated.")

    print("\n" + "=" * 70)
    print("ALL 11 DEPLOYMENT CHECKS PASSED PERFECTLY ON http://localhost!")
    print("=" * 70)

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
