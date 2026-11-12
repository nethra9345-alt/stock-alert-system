from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "StockPulse AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./stockpulse.db",
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

    INDICES: dict = {
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
