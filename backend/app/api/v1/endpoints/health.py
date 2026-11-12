import datetime
import pytz
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.services.market_service import is_indian_market_open

router = APIRouter()
IST = pytz.timezone("Asia/Kolkata")


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint to verify backend, database, and market connectivity."""
    db_status = "unhealthy"
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"

    is_open, market_msg = is_indian_market_open()

    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "current_time_ist": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "indian_market": {
            "is_open": is_open,
            "status_message": market_msg
        }
    }
