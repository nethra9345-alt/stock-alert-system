import time
import datetime
import pytz
from fastapi import APIRouter, Depends, Response, status
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
    raw_url = settings.DATABASE_URL.lower()
    if raw_url.startswith("sqlite"):
        db_type = "sqlite"
    elif "postgres" in raw_url:
        db_type = "postgresql"
    else:
        db_type = raw_url.split(":")[0]

    db_status = "connected"
    connectivity_result = "SELECT 1 successful"
    start_db = time.time()
    try:
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - start_db) * 1000, 2)
    except Exception as e:
        db_status = "error"
        db_latency_ms = -1
        connectivity_result = f"Failed to execute test query: {type(e).__name__}"

    is_open, market_msg = is_indian_market_open()
    verified_tables = sorted(list(Base.metadata.tables.keys()))

    return {
        "status": "online" if db_status == "connected" else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status,
            "database_type": db_type,
            "latency_ms": db_latency_ms,
            "connectivity_result": connectivity_result,
            "verified_tables": verified_tables
        },
        "current_time_ist": datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "indian_market": {
            "is_open": is_open,
            "status_message": market_msg
        }
    }


@router.get("/health/ready")
def readiness_check(response: Response, db: Session = Depends(get_db)):
    """Readiness probe for container orchestrators (Docker / K8s)."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "reachable", "timestamp": time.time()}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "database": "unreachable", "timestamp": time.time()}


@router.get("/health/live")
def liveness_check():
    """Liveness probe verifying HTTP event loop responsiveness."""
    return {"status": "alive", "timestamp": time.time()}
