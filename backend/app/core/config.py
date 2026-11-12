import os
from typing import List, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Project Root Directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_DB_FILE = os.path.join(BASE_DIR, "stockpulse.db").replace("\\", "/")
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_DB_FILE}"


class Settings(BaseSettings):
    PROJECT_NAME: str = "StockPulse AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database: SQLite by default with PostgreSQL compatibility
    # Set DATABASE_URL in .env to point to PostgreSQL in production
    DATABASE_URL: str = Field(
        default=DEFAULT_SQLITE_URL,
        description="SQLAlchemy database connection string. Can be PostgreSQL URL in production."
    )

    # CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000"
    ]

    # Market Configuration
    DEFAULT_CACHE_TTL: int = 60  # seconds

    INDICES: Dict[str, Any] = {
        "NIFTY 50": {"symbol": "^NSEI", "exchange": "NSE", "display_name": "NIFTY 50"},
        "SENSEX": {"symbol": "^BSESN", "exchange": "BSE", "display_name": "S&P BSE SENSEX"},
        "BANK NIFTY": {"symbol": "^NSEBANK", "exchange": "NSE", "display_name": "NIFTY BANK"},
        "INDIA VIX": {"symbol": "^INDIAVIX", "exchange": "NSE", "display_name": "INDIA VIX"}
    }

    WATCHLIST_DEFAULTS: List[str] = [
        "RELIANCE.NS",
        "TCS.NS",
        "HDFCBANK.NS",
        "INFY.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "BHARTIARTL.NS",
        "ITC.NS",
        "LT.NS",
        "TATAMOTORS.NS"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )


settings = Settings()
