# StockPulse AI — Demonstration Deployment & College Viva Guide
**Stage 11: Production Demonstration Deployment for Academic Evaluation**

---

## 1. Executive Summary & Objective

**StockPulse AI** is deployed on the host laptop as a multi-container Docker application accessible at:

```
http://localhost
```

This deployment is specifically configured for **academic project demonstrations, faculty evaluation, and viva examinations**. It preserves native database persistence, eliminates third-party cloud dependencies for local execution, and demonstrates production architectural patterns including container isolation, reverse proxying, and strict web application security.

---

## 2. Architecture & Container Topology

```
   ┌─────────────────────────────────────────────────────────────┐
   │                        Web Browser                          │
   │                   (Faculty / Examiner)                      │
   └──────────────────────────────┬──────────────────────────────┘
                                  │ HTTP Port 80
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │             stockpulse-frontend (Nginx 1.25)                │
   │  - Serves React 18 + Vite SPA Build                         │
   │  - Reverse proxies /api/  ──────► backend:8000/api/         │
   │  - Reverse proxies /docs  ──────► backend:8000/docs         │
   │  - Security headers: CSP, X-Frame-Options, X-Content-Type   │
   └──────────────────────────────┬──────────────────────────────┘
                                  │ Docker Bridge: stockpulse-net
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │             stockpulse-backend (FastAPI / Python 3.11)      │
   │  - Multi-stage hardened image (Non-root user: appuser)      │
   │  - Uvicorn ASGI Server                                      │
   │  - PyJWT Bearer Authentication & Double-Submit CSRF Guard   │
   │  - Quantitative Analytics & Technical Indicators Engine     │
   │  - Machine Learning Engine (XGBoost, Random Forest)         │
   └──────────────────────────────┬──────────────────────────────┘
                                  │ host.docker.internal:5432
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │           Windows Host PostgreSQL 18.7 Database             │
   │  - Database: stockpulse (19 application tables)             │
   │  - Alembic Head Revision: d45a76e90234                      │
   │  - 72 Users, active portfolios, watchlists, & event alerts  │
   │  - Preserved native storage without container data wipe     │
   └─────────────────────────────────────────────────────────────┘
```

### Key Architectural Highlights:
1. **Unified Port 80 Entry Point**: Faculty access both the responsive SPA dashboard and API endpoints seamlessly through standard HTTP (`http://localhost`) without memorizing port numbers.
2. **Windows Host PostgreSQL Bridge**: By routing database traffic through `host.docker.internal:5432`, the containerized application connects directly to the existing Windows PostgreSQL 18.7 service, guaranteeing zero data loss, preserving all user accounts, transactions, and migration history.
3. **Defense-in-Depth Security**:
   - Short-lived signed JWT access tokens (15-minute expiration).
   - HttpOnly SameSite refresh tokens stored in database with automatic rotation and revocation on logout.
   - Double-Submit CSRF cookie protection (`X-CSRF-Token` header validation).
   - Strict password hashing using industry-standard Bcrypt.

---

## 3. Quick Start & Demonstration Commands

### Step 1: Verify Windows PostgreSQL is Running
Open PowerShell or Services on Windows and verify PostgreSQL is active:
```powershell
Get-Service -Name postgresql*
```

### Step 2: Launch the Demonstration System
From the project root (`C:\Users\ASUS\Desktop\BIT\stock-alert-system`):
```bash
docker compose up -d
```

### Step 3: Verify Container Health
```bash
docker compose ps
```
Both `stockpulse-backend` and `stockpulse-frontend` will report `(healthy)`.

### Step 4: Open in Web Browser
- **Main Application Dashboard**: [http://localhost](http://localhost)
- **Interactive Swagger Documentation**: [http://localhost/docs](http://localhost/docs)
- **System Health & DB Probe**: [http://localhost/api/health](http://localhost/api/health)

### Step 5: Run Automated Live Compliance Suite
In front of the examiner, run the automated verification script:
```powershell
backend\venv\Scripts\python.exe scripts\verify_demo_deployment.py
```
This tests all 14 live subsystems over `http://localhost` in under 15 seconds.

---

## 4. Network Configuration & Windows Host Security (Stage 11.1)

To connect the containerized backend to native Windows PostgreSQL without creating a redundant database container or exposing database ports to public networks, the following configuration is enforced:

### 1. Docker Bridge Resolution (`host.docker.internal`)
- The `docker-compose.yml` backend service includes:
  ```yaml
  extra_hosts:
    - "host.docker.internal:host-gateway"
  ```
- This resolves `host.docker.internal` to the WSL2/Docker virtual network gateway IP (e.g. `192.168.65.254` or `172.17.0.1`), allowing outbound container TCP connections to reach port 5432 on the host.

### 2. PostgreSQL Configuration (`postgresql.conf` & `pg_hba.conf`)
- In `C:\Program Files\PostgreSQL\18\data\postgresql.conf`:
  ```ini
  listen_addresses = '*'
  ```
  *(Allows PostgreSQL to bind to local loopback and the Docker virtual interface).*
- In `C:\Program Files\PostgreSQL\18\data\pg_hba.conf`:
  ```text
  # TYPE  DATABASE        USER            ADDRESS                 METHOD
  # Local host connections:
  host    stockpulse      all             127.0.0.1/32            scram-sha-256
  host    stockpulse      all             ::1/128                 scram-sha-256
  # Docker bridge subnets only (never 0.0.0.0/0):
  host    stockpulse      all             172.16.0.0/12           scram-sha-256
  host    stockpulse      all             192.168.0.0/16          scram-sha-256
  ```

### 3. Windows Defender Firewall Policy
- Port 5432 is **NEVER** exposed to Public networks.
- A scoped inbound firewall rule restricts port 5432 strictly to `Domain` and `Private` profiles and local Docker adapter subnets:
  ```powershell
  # Verify port 5432 firewall rule scope:
  Get-NetFirewallRule -DisplayName "*PostgreSQL*" | Select-Object Name, Profile, Enabled, Action
  ```

---

## 5. Demonstration Accounts & User Personas

| Role | Username / Email | Password | Access & Features |
| :--- | :--- | :--- | :--- |
| **Active Pro Trader** *(Recommended)* | `trader_pro`<br>`trader@stockpulse.ai` | `TraderPass@2026` | Preloaded portfolio (₹106,350 invested), custom watchlist (RELIANCE, TCS, INFY, HDFCBANK), active price alerts, and market events. |
| **New Faculty / Examiner** | Self-Registration | Custom | Click **Register** on the login screen to demonstrate real-time Bcrypt hashing, instant JWT issuance, and database isolation. |

---

## 6. College Viva Walkthrough & Demonstration Script

### Segment 1: System Health & Architecture (2 mins)
1. Navigate to `http://localhost/api/health` in browser.
2. **Explain to Examiner**:
   - The health endpoint returns JSON telemetry proving that the FastAPI backend inside Docker is communicating with the Windows PostgreSQL database at ~5ms latency.
   - It lists 18 verified tables and displays the real-time status of Indian financial market trading sessions (NSE/BSE).

### Segment 2: Authentication & Security Hardening (3 mins)
1. Navigate to `http://localhost`. The login screen appears.
2. Log in using `trader_pro` / `TraderPass@2026`.
3. Open Chrome DevTools (`F12`) -> **Application** -> **Cookies**:
   - Show `stockpulse_refresh_token`: Marked as **HttpOnly** and **SameSite=Lax**. JavaScript cannot read it, preventing XSS-based session hijacking.
   - Show `stockpulse_csrf_token`: Passed in requests via custom header `X-CSRF-Token`, preventing Cross-Site Request Forgery.
4. Explain password security: Passwords are salted and hashed using **Bcrypt** (`$2b$12$...`), verified by the 105 automated unit tests.

### Segment 3: Market Overview & Technical Indicators (3 mins)
1. Go to **Market Overview**:
   - Displays NIFTY 50, SENSEX, BANK NIFTY, and INDIA VIX.
2. Select **RELIANCE.NS**:
   - View interactive candlestick/line charts with moving averages (SMA 20, SMA 50).
   - Wilder’s smoothed RSI (14-period) indicating overbought (>70) or oversold (<30) conditions.
   - MACD (12, 26, 9) signal line crossovers.

### Segment 4: Portfolio Risk Intelligence (3 mins)
1. Go to **Portfolio**:
   - Shows total invested capital, current valuation, and real-time P&L.
   - Highlights cost-basis accounting (FIFO/Weighted-Average) for BUY and SELL orders.
2. View **Risk Metrics**:
   - **Value-at-Risk (VaR 95% & 99%)**: Parametric and Historical simulation measuring maximum potential drawdown.
   - **Portfolio Beta**: Sensitivity relative to NIFTY 50 index benchmark.
   - **Sharpe Ratio**: Risk-adjusted return calculation.

### Segment 5: Quantitative Forecasting & ML Model Audit (3 mins)
1. Go to **AI Insights / Predictions**:
   - Multi-model comparative forecasting: **Persistence Baseline vs. Random Forest vs. XGBoost**.
   - **No Future Leakage**: Strictly trained on chronological historical splits.
   - Displays evaluation metrics: Mean Absolute Error (MAE), RMSE, and Directional Accuracy.
   - Explain why the persistence baseline is mandatory in quantitative finance to prove statistical edge.

### Segment 6: AI Stock Assistant & Sentiment Intelligence (3 mins)
1. Go to **AI Research Assistant**:
   - Ask: *"Analyze RELIANCE.NS technical signals and volume anomalies."*
   - Demonstrates Retrieval-Augmented Generation (RAG) synthesizing real database events, technical indicator values, and company news.
   - Transparent citations: Discloses whether answers are derived from local rule engines or external LLMs.

---

## 7. Frequently Asked Viva Questions & Answers

### Q1: Why did you run the application in Docker instead of standard local processes?
> **Answer**: Docker Compose provides containerized isolation, ensuring reproducibility across environments regardless of host operating system quirks. It mirrors production deployment architectures with an Nginx reverse proxy fronting an ASGI backend, while isolating application dependencies from the host system.

### Q2: How does the backend inside Docker connect to the PostgreSQL running on Windows?
> **Answer**: Docker Desktop for Windows provides the DNS entry `host.docker.internal`, which maps to the host gateway IP. The backend container communicates with Windows PostgreSQL over `host.docker.internal:5432`. We also configured PostgreSQL's `pg_hba.conf` and `listen_addresses = '*'` to safely permit connections from local Docker bridge networks.

### Q3: Why is Nginx used as a reverse proxy in front of FastAPI?
> **Answer**: Nginx handles static file compression (Gzip), TLS termination, unified CORS/header management, and routing. Serving the React SPA directly from Nginx and reverse-proxying `/api/` to FastAPI on port 80 avoids cross-origin requests, eliminates browser CORS restrictions, and protects the Python ASGI server from slow-client attacks.

### Q4: How is CSRF prevented in a modern SPA?
> **Answer**: We employ the **Double-Submit Cookie pattern**. On authentication, the backend sets a cryptographically random CSRF token in an accessible cookie and the client echoes this token in the custom `X-CSRF-Token` header for state-changing requests (POST, PUT, DELETE). Browsers enforce the Same-Origin Policy, preventing unauthorized third-party domains from reading the cookie or spoofing the header.

### Q5: How do you verify that your ML models do not suffer from data leakage?
> **Answer**: We enforce strict **chronological train-validation-test splitting** instead of random k-fold cross-validation. Features are lagged so that time $t$ only uses information available up to session $t-1$. Furthermore, every model is compared against a **Persistence Baseline** ($y_t = y_{t-1}$) to objectively measure genuine predictive edge.

---

## 8. Teardown & Maintenance

To stop the demonstration deployment cleanly:
```bash
docker compose down
```

To stop without deleting networks:
```bash
docker compose stop
```

To view live container logs during the demo:
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

