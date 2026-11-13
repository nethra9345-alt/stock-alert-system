import os
from typing import List, Dict, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Project Directories
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASE_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
ENV_FILE = os.path.join(BACKEND_DIR, ".env")
DEFAULT_DB_FILE = os.path.join(BASE_DIR, "stockpulse.db").replace("\\", "/")
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_DB_FILE}"


class Settings(BaseSettings):
    PROJECT_NAME: str = "StockPulse AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database: Supports PostgreSQL (postgresql+psycopg://) and SQLite (sqlite:///)
    # Read from environment variable or backend/.env; falls back to SQLite if unset
    DATABASE_URL: str = Field(
        default=DEFAULT_SQLITE_URL,
        description="SQLAlchemy database connection string. PostgreSQL or SQLite."
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Authentication & Security
    JWT_SECRET_KEY: str = Field(
        default="stockpulse-dev-secret-key-replace-in-production-with-env-variable",
        description="Secret key for signing JSON Web Tokens"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RATE_LIMIT_PER_MINUTE: int = 120
    AUTH_RATE_LIMIT_PER_MINUTE: int = 20
    MAX_REQUEST_SIZE_BYTES: int = 10 * 1024 * 1024

    # CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000"
    ]

    # AI / LLM Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

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
        env_file=ENV_FILE,
        case_sensitive=True,
        extra="allow"
    )


settings = Settings()
