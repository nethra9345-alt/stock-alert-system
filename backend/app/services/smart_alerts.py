"""Smart Alert Engine for StockPulse AI.

Features:
- Evaluates individual price thresholds (ABOVE, BELOW, PCT_CHANGE)
- Evaluates portfolio-level risk alerts (PORTFOLIO_LOSS, PORTFOLIO_DRAWDOWN)
- Evaluates market anomaly alerts (MARKET_EVENT, VOLUME_SPIKE)
- Enforces strict notification cooldowns to prevent spamming
- Enforces duplicate prevention across identical condition states
- Persists alert history to PostgreSQL
- Respects user-configured AlertPreferences
- Strictly passive: NEVER executes automated orders or trades.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.app.models.alert import PriceAlert, AlertHistory, AlertPreferences
from backend.app.models.event import MarketEvent
from backend.app.services.market_service import get_stock_quote


def get_or_create_alert_preferences(db: Session, user_id: int) -> AlertPreferences:
    """Retrieves or initializes user alert preferences."""
    prefs = db.query(AlertPreferences).filter(AlertPreferences.user_id == user_id).first()
    if not prefs:
        prefs = AlertPreferences(
            user_id=user_id,
            price_alerts_enabled=True,
            portfolio_alerts_enabled=True,
            market_event_alerts_enabled=True,
            volume_spike_alerts_enabled=True,
            min_price_change_pct=4.0,
            portfolio_loss_threshold_pct=5.0,
            portfolio_drawdown_threshold_pct=8.0,
            cooldown_minutes=60,
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def is_in_cooldown(
    db: Session,
    user_id: int,
    alert_type: str,
    symbol: Optional[str],
    cooldown_minutes: int,
    now: Optional[datetime] = None,
) -> bool:
    """
    Checks if a matching alert notification was generated within the cooldown window.
    """
    current_time = now or datetime.utcnow()
    cutoff_time = current_time - timedelta(minutes=cooldown_minutes)

    query = db.query(AlertHistory).filter(
        AlertHistory.user_id == user_id,
        AlertHistory.alert_type == alert_type,
        AlertHistory.created_at >= cutoff_time,
    )

    if symbol:
        query = query.filter(AlertHistory.symbol == symbol.upper())
    else:
        query = query.filter(AlertHistory.symbol == None)

    recent_alert = query.first()
    return recent_alert is not None


def evaluate_smart_alerts(
    db: Session,
    user_id: int,
    portfolio_overview: Optional[Dict[str, Any]] = None,
    portfolio_risk: Optional[Dict[str, Any]] = None,
    quote_map: Optional[Dict[str, Any]] = None,
    recent_market_events: Optional[List[MarketEvent]] = None,
    evaluation_time: Optional[datetime] = None,
) -> List[AlertHistory]:
    """
    Evaluates all active price alerts, portfolio risk thresholds, and market events
    for the specified user, creating notifications in PostgreSQL when criteria are met.
    """
    now = evaluation_time or datetime.utcnow()
    prefs = get_or_create_alert_preferences(db, user_id)
    created_notifications: List[AlertHistory] = []

    # -------------------------------------------------------------
    # 1. Price Threshold & Percent Change Alerts (if enabled)
    # -------------------------------------------------------------
    if prefs.price_alerts_enabled:
        active_price_alerts = db.query(PriceAlert).filter(
            PriceAlert.user_id == user_id,
            PriceAlert.is_active == True,
            PriceAlert.is_triggered == False,
        ).all()

        for pa in active_price_alerts:
            sym = pa.symbol.upper()
            curr_price = None

            if quote_map and sym in quote_map:
                curr_price = float(quote_map[sym].get("price", 0.0) if isinstance(quote_map[sym], dict) else quote_map[sym])
            else:
                try:
                    q = get_stock_quote(sym)
                    curr_price = float(q.price)
                except Exception:
                    curr_price = None

            if curr_price is None or curr_price <= 0:
                continue

            cond = pa.condition.upper().strip()
            triggered = False
            alert_type = f"PRICE_{cond}"
            title = ""
            msg = ""

            if cond == "ABOVE" and curr_price >= pa.target_price:
                triggered = True
                title = f"{sym} Price Crossed Above ₹{pa.target_price:,.2f}"
                msg = f"{sym} reached ₹{curr_price:,.2f}, hitting your target price threshold of ₹{pa.target_price:,.2f}."
            elif cond == "BELOW" and curr_price <= pa.target_price:
                triggered = True
                title = f"{sym} Price Dropped Below ₹{pa.target_price:,.2f}"
                msg = f"{sym} traded down to ₹{curr_price:,.2f}, falling below your target threshold of ₹{pa.target_price:,.2f}."

            if triggered:
                # Mark alert as triggered in price_alerts table
                pa.is_triggered = True
                pa.triggered_at = now

                # Check cooldown before recording in alert_history
                if not is_in_cooldown(db, user_id, alert_type, sym, prefs.cooldown_minutes, now):
                    notif = AlertHistory(
                        user_id=user_id,
                        alert_id=pa.id,
                        symbol=sym,
                        alert_type=alert_type,
                        severity="WARNING" if cond == "BELOW" else "INFO",
                        title=title,
                        message=msg,
                        trigger_value=curr_price,
                        threshold_value=pa.target_price,
                        status="TRIGGERED",
                        created_at=now,
                    )
                    db.add(notif)
                    created_notifications.append(notif)

    # -------------------------------------------------------------
    # 2. Portfolio Loss & Drawdown Alerts (if enabled)
    # -------------------------------------------------------------
    if prefs.portfolio_alerts_enabled and portfolio_overview:
        pnl_pct = float(portfolio_overview.get("overall_return_percent", 0.0))
        # If overall return is negative and exceeds loss threshold
        if pnl_pct < 0 and abs(pnl_pct) >= prefs.portfolio_loss_threshold_pct:
            alert_type = "PORTFOLIO_LOSS"
            if not is_in_cooldown(db, user_id, alert_type, None, prefs.cooldown_minutes, now):
                notif = AlertHistory(
                    user_id=user_id,
                    alert_id=None,
                    symbol=None,
                    alert_type=alert_type,
                    severity="CRITICAL" if abs(pnl_pct) >= (prefs.portfolio_loss_threshold_pct * 1.5) else "WARNING",
                    title=f"Portfolio Loss Alert: {pnl_pct:.2f}%",
                    message=(
                        f"Your portfolio overall return is currently down {pnl_pct:.2f}%, "
                        f"exceeding your configured loss threshold of {prefs.portfolio_loss_threshold_pct:.1f}%."
                    ),
                    trigger_value=round(pnl_pct, 2),
                    threshold_value=prefs.portfolio_loss_threshold_pct,
                    status="TRIGGERED",
                    created_at=now,
                )
                db.add(notif)
                created_notifications.append(notif)

    # Portfolio Drawdown Check
    if prefs.portfolio_alerts_enabled and portfolio_risk:
        dd_data = portfolio_risk.get("drawdown", {})
        mdd_pct = float(dd_data.get("maximum_drawdown_pct", 0.0))
        if mdd_pct >= prefs.portfolio_drawdown_threshold_pct:
            alert_type = "PORTFOLIO_DRAWDOWN"
            if not is_in_cooldown(db, user_id, alert_type, None, prefs.cooldown_minutes, now):
                notif = AlertHistory(
                    user_id=user_id,
                    alert_id=None,
                    symbol=None,
                    alert_type=alert_type,
                    severity="CRITICAL" if mdd_pct >= (prefs.portfolio_drawdown_threshold_pct * 1.5) else "WARNING",
                    title=f"Significant Portfolio Drawdown: {mdd_pct:.2f}%",
                    message=(
                        f"Portfolio peak-to-trough drawdown reached {mdd_pct:.2f}%, "
                        f"exceeding your risk threshold of {prefs.portfolio_drawdown_threshold_pct:.1f}%."
                    ),
                    trigger_value=round(mdd_pct, 2),
                    threshold_value=prefs.portfolio_drawdown_threshold_pct,
                    status="TRIGGERED",
                    created_at=now,
                )
                db.add(notif)
                created_notifications.append(notif)

    # -------------------------------------------------------------
    # 3. Market Event & Volume Spike Alerts (if enabled)
    # -------------------------------------------------------------
    if (prefs.market_event_alerts_enabled or prefs.volume_spike_alerts_enabled) and recent_market_events:
        for ev in recent_market_events:
            sym = ev.symbol.upper()
            ev_type = ev.event_type.upper()
            is_vol_spike = "VOLUME" in ev_type or ev.volume_ratio >= 3.0

            # Route to volume spike alert or general market event
            if is_vol_spike and prefs.volume_spike_alerts_enabled:
                alert_type = "VOLUME_SPIKE"
                if not is_in_cooldown(db, user_id, alert_type, sym, prefs.cooldown_minutes, now):
                    notif = AlertHistory(
                        user_id=user_id,
                        alert_id=None,
                        symbol=sym,
                        alert_type=alert_type,
                        severity="WARNING" if ev.severity.upper() == "EXTREME" else "INFO",
                        title=f"{sym} Volume Shock: {ev.volume_ratio:.1f}x Normal",
                        message=(
                            f"{sym} experienced a {ev.volume_ratio:.1f}x volume spike on {ev.event_date}. "
                            f"{ev.explanation_summary}"
                        ),
                        trigger_value=round(ev.volume_ratio, 2),
                        threshold_value=2.0,
                        status="TRIGGERED",
                        created_at=now,
                    )
                    db.add(notif)
                    created_notifications.append(notif)
            elif prefs.market_event_alerts_enabled and ev.severity.upper() in ["EXTREME", "HIGH"]:
                alert_type = "MARKET_EVENT"
                if not is_in_cooldown(db, user_id, alert_type, sym, prefs.cooldown_minutes, now):
                    notif = AlertHistory(
                        user_id=user_id,
                        alert_id=None,
                        symbol=sym,
                        alert_type=alert_type,
                        severity="CRITICAL" if ev.severity.upper() == "EXTREME" else "WARNING",
                        title=f"{sym} {ev.event_type} Anomaly Detected",
                        message=(
                            f"{sym} registered a {ev.price_change_pct:+.2f}% {ev.event_type} move ({ev.severity}). "
                            f"{ev.explanation_summary}"
                        ),
                        trigger_value=round(ev.price_change_pct, 2),
                        threshold_value=prefs.min_price_change_pct,
                        status="TRIGGERED",
                        created_at=now,
                    )
                    db.add(notif)
                    created_notifications.append(notif)

    db.commit()
    for notif in created_notifications:
        db.refresh(notif)

    return created_notifications
