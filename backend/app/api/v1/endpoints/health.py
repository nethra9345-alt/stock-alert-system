import datetime
import pytz
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.core.database import get_db, Base
from backend.app.services.market_service import is_indian_market_open

router = APIRouter()
IST = pytz.timezone("Asia/Kolkata")


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint returning system status, sanitized database connectivity,
    and Indian financial market session status without exposing credentials.
    """
    # Detect sanitized database type
    raw_url = settings.DATABASE_URL.lower()
    if raw_url.startswith("sqlite"):
        db_type = "sqlite"
    elif "postgres" in raw_url:
        db_type = "postgresql"
    else:
        db_type = raw_url.split(":")[0]

    db_status = "connected"
    connectivity_result = "SELECT 1 successful"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        connectivity_result = f"Failed to execute test query: {type(e).__name__}"

    is_open, market_msg = is_indian_market_open()
    verified_tables = sorted(list(Base.metadata.tables.keys()))

    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status,
            "database_type": db_type,
            "connectivity_result": connectivity_result,
            "verified_tables": verified_tables
        },
        "current_time_ist": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "indian_market": {
            "is_open": is_open,
            "status_message": market_msg
        }
    }
