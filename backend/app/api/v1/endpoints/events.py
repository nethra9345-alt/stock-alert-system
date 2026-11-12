from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.models.event import MarketEvent
from backend.app.schemas.event import (
    MarketEventRead,
    MarketEventListResponse,
    AnalyzeEventsRequest,
    AnalyzeEventsResponse
)
from backend.app.services.market_service import (
    normalize_symbol,
    get_stock_history_df,
    SYMBOL_METADATA
)
from backend.app.services.event_detection import detect_market_events_from_df
from backend.app.services.event_explainer import generate_event_explanation

router = APIRouter()


@router.get("", response_model=MarketEventListResponse)
def list_market_events(
    symbol: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    is_verified: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Retrieves all detected market events with optional symbol, type, and severity filtering."""
    query = db.query(MarketEvent)

    if symbol:
        norm_sym = normalize_symbol(symbol)
        query = query.filter(MarketEvent.symbol == norm_sym)

    if event_type:
        query = query.filter(MarketEvent.event_type == event_type.upper())

    if severity:
        query = query.filter(MarketEvent.severity == severity.upper())

    if is_verified is not None:
        query = query.filter(MarketEvent.is_verified == is_verified)

    total_count = query.count()
    events = (
        query.order_by(desc(MarketEvent.event_date), desc(MarketEvent.id))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return MarketEventListResponse(count=total_count, events=events)


@router.get("/{symbol}", response_model=MarketEventListResponse)
def get_events_for_symbol(
    symbol: str,
    event_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Retrieves detected market events for a specific NSE/BSE stock."""
    norm_sym = normalize_symbol(symbol)
    query = db.query(MarketEvent).filter(MarketEvent.symbol == norm_sym)

    if event_type:
        query = query.filter(MarketEvent.event_type == event_type.upper())

    total_count = query.count()
    events = (
        query.order_by(desc(MarketEvent.event_date), desc(MarketEvent.id))
        .limit(limit)
        .all()
    )

    return MarketEventListResponse(count=total_count, events=events)


@router.get("/{symbol}/latest", response_model=MarketEventRead)
def get_latest_event_for_symbol(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Retrieves the single most recent market anomaly event for a stock."""
    norm_sym = normalize_symbol(symbol)
    latest = (
        db.query(MarketEvent)
        .filter(MarketEvent.symbol == norm_sym)
        .order_by(desc(MarketEvent.event_date), desc(MarketEvent.id))
        .first()
    )

    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No detected market events on record for {symbol}"
        )

    return latest


@router.post("/{symbol}/analyze", response_model=AnalyzeEventsResponse)
def analyze_and_detect_events(
    symbol: str,
    req: AnalyzeEventsRequest = AnalyzeEventsRequest(),
    db: Session = Depends(get_db)
):
    """
    Scans historical OHLCV data for statistical/technical anomalies (price surges, drops, gap-ups,
    volume spikes, breakouts), generates explanations backed by verified news, and persists them.
    Guarantees idempotency via unique constraints.
    """
    norm_sym = normalize_symbol(symbol)
    meta = SYMBOL_METADATA.get(norm_sym, {})
    company_name = meta.get("name") or norm_sym.replace(".NS", "").replace(".BO", "")

    # 1. Fetch historical OHLCV data
    df, _, _ = get_stock_history_df(norm_sym, period=req.period, interval="1d")
    if df.empty or len(df) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient historical data available to analyze {symbol}"
        )

    # 2. Detect statistical anomalies
    detected = detect_market_events_from_df(
        df=df,
        symbol=norm_sym,
        company_name=company_name,
        price_threshold_pct=req.price_threshold_pct,
        volume_ratio_threshold=req.volume_ratio_threshold
    )

    newly_persisted = 0

    # 3. Process each event with the AI explanation service and persist
    for item in detected:
        # Check if identical record already exists in database
        existing = (
            db.query(MarketEvent)
            .filter(
                MarketEvent.symbol == norm_sym,
                MarketEvent.event_type == item["event_type"],
                MarketEvent.event_date == item["event_date"]
            )
            .first()
        )

        if existing:
            # If exists but has no explanation yet, populate explanation
            if not existing.explanation_summary:
                explanation = generate_event_explanation(item)
                existing.explanation_summary = explanation["explanation_summary"]
                existing.explanation_detail = explanation["explanation_detail"]
                existing.sources = explanation["sources"]
                existing.is_verified = explanation["is_verified"]
                db.commit()
            continue

        # Generate objective verified explanation
        explanation = generate_event_explanation(item)
        item["explanation_summary"] = explanation["explanation_summary"]
        item["explanation_detail"] = explanation["explanation_detail"]
        item["sources"] = explanation["sources"]
        item["is_verified"] = explanation["is_verified"]

        event_model = MarketEvent(**item)
        db.add(event_model)
        newly_persisted += 1

    if newly_persisted > 0:
        db.commit()

    # 4. Fetch all events on record for this symbol
    all_events = (
        db.query(MarketEvent)
        .filter(MarketEvent.symbol == norm_sym)
        .order_by(desc(MarketEvent.event_date), desc(MarketEvent.id))
        .all()
    )

    return AnalyzeEventsResponse(
        symbol=norm_sym,
        company_name=company_name,
        analyzed_sessions=len(df),
        detected_events_count=len(detected),
        newly_persisted_count=newly_persisted,
        events=all_events
    )
