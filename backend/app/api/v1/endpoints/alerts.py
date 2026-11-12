import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.models.alert import PriceAlert, AlertHistory, AlertPreferences
from backend.app.models.event import MarketEvent
from backend.app.schemas.alert import (
    AlertCreate,
    AlertResponse,
    AlertHistoryItem,
    AlertPreferencesRead,
    AlertPreferencesUpdate,
    AlertEvaluateResponse,
)
from backend.app.services.market_service import get_stock_quote, normalize_symbol
from backend.app.services.portfolio_analytics import compute_fifo_portfolio_holdings
from backend.app.services.portfolio_risk import calculate_portfolio_risk
from backend.app.services.smart_alerts import (
    get_or_create_alert_preferences,
    evaluate_smart_alerts,
)

router = APIRouter()


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches user price alerts and evaluates against current stock prices."""
    alerts = db.query(PriceAlert).filter(
        PriceAlert.user_id == current_user.id
    ).order_by(PriceAlert.created_at.desc()).all()

    # Seed initial alerts for user 1 if empty
    if not alerts and current_user.id == 1:
        seed = [
            ("RELIANCE.NS", 3050.0, "ABOVE", "Reliance resistance target"),
            ("TCS.NS", 4000.0, "BELOW", "TCS buy dip alert"),
            ("HDFCBANK.NS", 1700.0, "ABOVE", "HDFC breakout target")
        ]
        for sym, tgt, cond, note in seed:
            q = get_stock_quote(sym)
            a = PriceAlert(
                user_id=current_user.id,
                symbol=sym,
                company_name=q.name,
                target_price=tgt,
                condition=cond,
                notes=note
            )
            db.add(a)
        db.commit()
        alerts = db.query(PriceAlert).filter(PriceAlert.user_id == current_user.id).all()

    results = []
    for a in alerts:
        q = get_stock_quote(a.symbol)
        curr_price = q.price

        # Evaluate condition if active and not already triggered
        if a.is_active and not a.is_triggered:
            triggered = False
            if a.condition == "ABOVE" and curr_price >= a.target_price:
                triggered = True
            elif a.condition == "BELOW" and curr_price <= a.target_price:
                triggered = True

            if triggered:
                a.is_triggered = True
                a.triggered_at = datetime.datetime.utcnow()
                db.commit()

        results.append(AlertResponse(
            id=a.id,
            user_id=a.user_id,
            symbol=a.symbol,
            company_name=a.company_name or q.name,
            target_price=a.target_price,
            condition=a.condition,
            is_active=a.is_active,
            is_triggered=a.is_triggered,
            triggered_at=a.triggered_at,
            notes=a.notes,
            created_at=a.created_at,
            current_price=curr_price
        ))

    return results


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    data: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new price alert isolated to current user."""
    cond = data.condition.upper()
    if cond not in ["ABOVE", "BELOW"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Condition must be 'ABOVE' or 'BELOW'"
        )

    norm_sym = normalize_symbol(data.symbol)
    q = get_stock_quote(norm_sym)

    alert = PriceAlert(
        user_id=current_user.id,
        symbol=norm_sym,
        company_name=data.company_name or q.name,
        target_price=data.target_price,
        condition=cond,
        notes=data.notes,
        is_active=True,
        is_triggered=False
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return AlertResponse(
        id=alert.id,
        user_id=alert.user_id,
        symbol=alert.symbol,
        company_name=alert.company_name,
        target_price=alert.target_price,
        condition=alert.condition,
        is_active=alert.is_active,
        is_triggered=alert.is_triggered,
        triggered_at=alert.triggered_at,
        notes=alert.notes,
        created_at=alert.created_at,
        current_price=q.price
    )


@router.patch("/{alert_id}/toggle", response_model=AlertResponse)
def toggle_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggles alert active status for an alert belonging to user."""
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.is_active = not alert.is_active
    db.commit()
    db.refresh(alert)
    q = get_stock_quote(alert.symbol)

    return AlertResponse(
        id=alert.id,
        user_id=alert.user_id,
        symbol=alert.symbol,
        company_name=alert.company_name,
        target_price=alert.target_price,
        condition=alert.condition,
        is_active=alert.is_active,
        is_triggered=alert.is_triggered,
        triggered_at=alert.triggered_at,
        notes=alert.notes,
        created_at=alert.created_at,
        current_price=q.price
    )


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes an alert belonging to current user."""
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    db.delete(alert)
    db.commit()
    return {"status": "success", "message": "Alert deleted"}


# -----------------------------------------------------------------
# Stage 6: Smart Alert History & Notifications Endpoints
# -----------------------------------------------------------------

@router.get("/history", response_model=List[AlertHistoryItem])
def get_alert_history(
    status_filter: Optional[str] = Query(None, alias="status", description="TRIGGERED, ACKNOWLEDGED, RESOLVED"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves chronological history of triggered smart alerts for the current user.
    """
    query = db.query(AlertHistory).filter(AlertHistory.user_id == current_user.id)
    if status_filter:
        query = query.filter(AlertHistory.status == status_filter.upper())

    return query.order_by(AlertHistory.created_at.desc()).limit(limit).all()


@router.post("/history/{history_id}/acknowledge", response_model=AlertHistoryItem)
def acknowledge_alert(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marks a triggered alert notification as acknowledged by the user.
    """
    item = db.query(AlertHistory).filter(
        AlertHistory.id == history_id,
        AlertHistory.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert notification not found")

    item.status = "ACKNOWLEDGED"
    item.acknowledged_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


@router.post("/history/{history_id}/resolve", response_model=AlertHistoryItem)
def resolve_alert(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marks an alert notification as resolved.
    """
    item = db.query(AlertHistory).filter(
        AlertHistory.id == history_id,
        AlertHistory.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert notification not found")

    item.status = "RESOLVED"
    item.resolved_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


# -----------------------------------------------------------------
# Stage 6: Alert Preferences Endpoints
# -----------------------------------------------------------------

@router.get("/preferences", response_model=AlertPreferencesRead)
def get_alert_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the user's smart alert preferences and notification thresholds.
    """
    return get_or_create_alert_preferences(db, current_user.id)


@router.put("/preferences", response_model=AlertPreferencesRead)
def update_alert_preferences(
    data: AlertPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the user's smart alert preferences and cooldown settings.
    """
    prefs = get_or_create_alert_preferences(db, current_user.id)

    update_dict = data.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        if v is not None:
            setattr(prefs, k, v)

    prefs.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(prefs)
    return prefs


# -----------------------------------------------------------------
# Stage 6: On-demand Smart Alert Evaluation Engine
# -----------------------------------------------------------------

@router.post("/evaluate", response_model=AlertEvaluateResponse)
def run_alert_evaluation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluates all active price alerts, portfolio loss thresholds, and market events
    for the current user, recording any new notifications in PostgreSQL with cooldown guards.
    """
    from backend.app.models.portfolio import PortfolioTransaction
    from backend.app.services.portfolio_analytics import compute_fifo_portfolio_holdings
    from backend.app.services.portfolio_risk import calculate_portfolio_risk

    # 1. Fetch user portfolio
    txs = db.query(PortfolioTransaction).filter(PortfolioTransaction.user_id == current_user.id).all()
    port_overview = None
    port_risk = None

    if txs:
        port_overview = compute_fifo_portfolio_holdings(txs)
        active_holdings = [h for h in port_overview["holdings"] if h["total_quantity"] > 0]
        if active_holdings:
            port_risk = calculate_portfolio_risk(active_holdings, period="3mo")

    # 2. Fetch recent market events (last 7 days)
    seven_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    recent_events = db.query(MarketEvent).filter(MarketEvent.event_date >= seven_days_ago).all()

    # 3. Evaluate alerts
    new_alerts = evaluate_smart_alerts(
        db=db,
        user_id=current_user.id,
        portfolio_overview=port_overview,
        portfolio_risk=port_risk,
        recent_market_events=recent_events,
    )

    return AlertEvaluateResponse(
        evaluated_at=datetime.datetime.utcnow(),
        new_alerts_triggered_count=len(new_alerts),
        alerts=new_alerts,
    )
