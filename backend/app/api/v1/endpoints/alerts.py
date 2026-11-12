import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.models.alert import PriceAlert
from backend.app.schemas.alert import AlertCreate, AlertResponse
from backend.app.services.market_service import get_stock_quote, normalize_symbol

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
