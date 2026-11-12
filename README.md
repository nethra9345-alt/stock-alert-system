# StockPulse AI — Indian Stock Market Intelligence Platform

**StockPulse AI** is an advanced, production-grade Indian Stock Market Intelligence Platform built for NSE and BSE equities. It integrates live market feeds, algorithmic technical indicators (Wilder's RSI, MACD, SMAs, EMAs), multi-model machine learning forecasting (Random Forest, XGBoost, and Persistence Baseline), and persistent portfolio and alert tracking backed by PostgreSQL 18.

---

## 🏛 Architecture Overview

```
stock-alert-system/
├── backend/                  # Python FastAPI Backend
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/v1/           # REST endpoints (health, market, stocks, watchlist, portfolio, alerts, ML)
│   │   ├── core/             # Configuration, PostgreSQL engine, user auth dependencies
│   │   ├── ml/               # Quantitative feature engineering & inference engine
│   │   ├── models/           # SQLAlchemy ORM models (User, WatchlistItem, PortfolioTransaction, PriceAlert)
│   │   ├── schemas/          # Pydantic v2 data validation schemas
│   │   └── services/         # Market data ingestion (yfinance) & technical indicators engine
│   └── tests/                # Pytest integration & unit test suite (31 tests)
├── frontend/                 # React + Vite Dark Fintech Dashboard
│   ├── src/
│   │   ├── components/       # IndexCard, StockChart (Recharts), Sidebar, TopNav, Badge, etc.
│   │   ├── pages/            # Dashboard, MarketOverview, StockExplorer, Watchlist, Portfolio, AIInsights, Alerts, Settings
│   │   ├── services/         # Centralized Axios client & API integrations
│   │   └── types/            # TypeScript data contracts & models
│   └── dist/                 # Production-optimized static build bundle
└── legacy_warehouse/         # Safely preserved original warehouse prototypes
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python**: 3.11+
- **Node.js**: v18+ (tested on v24.14.1)
- **PostgreSQL**: PostgreSQL 18 on `localhost:5432` with database `stockpulse`

---

### 2. Backend Setup & Startup

1. **Activate Virtual Environment**:
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   ```

2. **Configure Environment Variables**:
   Ensure `backend/.env` contains your PostgreSQL credentials:
   ```env
   DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@localhost:5432/stockpulse
   ENVIRONMENT=development
   ```

3. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

4. **Start FastAPI Application Server**:
   ```bash
   uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - API Documentation (Swagger UI): `http://127.0.0.1:8000/docs`
   - Health Probe: `http://127.0.0.1:8000/api/health`

---

### 3. Frontend Setup & Startup

1. **Install Dependencies & Build**:
   ```powershell
   cd frontend
   npm install
   npm run build
   ```

2. **Start Vite Development Server**:
   ```bash
   npm run dev
   ```
   The application dashboard will be live at `http://localhost:5173`.
   Vite is configured to automatically proxy `/api` requests to `http://127.0.0.1:8000`.

---

## 🧪 Testing & Verification

### Run Full Pytest Backend Test Suite:
```powershell
backend\venv\Scripts\python.exe -m pytest backend/tests -v
```
- **31 of 31 tests passing**:
  - API endpoints verification (`test_api.py`)
  - PostgreSQL CRUD, session management, and user data isolation (`test_database.py`)
  - Mathematical indicator verification against standard financial formulas (`test_indicators.py`)
  - ML walk-forward validation and zero target-leakage assertion (`test_ml.py`)

### Run Frontend TypeScript & Production Build:
```powershell
cd frontend
npm run build
```

---

## ⚠️ Financial Risk Disclaimer

StockPulse AI is strictly an **educational and analytical platform**. All price predictions, technical indicators, and quantitative scores are mathematical estimations derived from historical OHLCV data. They do **not** constitute investment advice, financial counsel, or guarantees of future market performance. Always conduct independent research or consult a SEBI-registered financial advisor before trading.
