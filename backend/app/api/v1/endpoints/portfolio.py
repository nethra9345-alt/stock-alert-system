from typing import Dict, List, Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.models.portfolio import PortfolioTransaction
from backend.app.schemas.portfolio import (
    PortfolioOverview,
    HoldingSummary,
    HoldingPerformance,
    StockAllocation,
    PortfolioTransactionCreate,
    PortfolioTransactionResponse,
    PortfolioAnalyticsResponse,
    PortfolioPerformanceResponse,
    PortfolioAllocationResponse,
    PortfolioRiskResponse,
)
from backend.app.services.market_service import get_stock_quote, normalize_symbol
from backend.app.services.portfolio_analytics import compute_fifo_portfolio_holdings
from backend.app.services.portfolio_risk import calculate_portfolio_risk

router = APIRouter()


def _ensure_seed_transactions_for_user(db: Session, user_id: int) -> List[PortfolioTransaction]:
    """Helper to ensure user 1 has demo transactions for initial dev/testing if empty."""
    transactions = db.query(PortfolioTransaction).filter(
        PortfolioTransaction.user_id == user_id
    ).all()

    if not transactions and user_id == 1 and settings.is_demo_allowed:
        seed_data = [
            ("RELIANCE.NS", "BUY", 10, 2850.00, "Reliance Industries"),
            ("TCS.NS", "BUY", 5, 3950.00, "Tata Consultancy Services"),
            ("INFY.NS", "BUY", 20, 1720.00, "Infosys Ltd"),
            ("HDFCBANK.NS", "BUY", 15, 1580.00, "HDFC Bank Ltd"),
        ]
        for sym, t_type, qty, price, name in seed_data:
            tx = PortfolioTransaction(
                user_id=user_id,
                symbol=sym,
                company_name=name,
                transaction_type=t_type,
                quantity=qty,
                purchase_price=price,
            )
            db.add(tx)
        db.commit()
        transactions = db.query(PortfolioTransaction).filter(
            PortfolioTransaction.user_id == user_id
        ).all()

    return transactions


@router.get("", response_model=PortfolioOverview)
def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes aggregated portfolio metrics, positions, and live P&L for current user.
    Preserves backward compatibility with Stage 2-4 schema.
    """
    transactions = _ensure_seed_transactions_for_user(db, current_user.id)
    fifo_data = compute_fifo_portfolio_holdings(transactions)

    holdings_list = []
    for h in fifo_data["holdings"]:
        if h["total_quantity"] > 0:
            holdings_list.append(HoldingSummary(
                symbol=h["symbol"],
                company_name=h["company_name"],
                exchange=h["exchange"],
                total_quantity=round(h["total_quantity"], 2),
                avg_buy_price=round(h["avg_buy_price"], 2),
                invested_value=round(h["invested_value"], 2),
                current_price=round(h["current_price"], 2),
                current_value=round(h["current_value"], 2),
                unrealized_pnl=round(h["unrealized_pnl"], 2),
                unrealized_pnl_percent=round(h["unrealized_pnl_percent"], 2),
            ))

    return PortfolioOverview(
        total_invested=round(fifo_data["total_invested"], 2),
        current_portfolio_value=round(fifo_data["current_portfolio_value"], 2),
        total_pnl=round(fifo_data["total_pnl"], 2),
        total_pnl_percent=round(fifo_data["overall_return_percent"], 2),
        holdings_count=len(holdings_list),
        holdings=holdings_list,
    )


@router.get("/analytics", response_model=PortfolioAnalyticsResponse)
def get_portfolio_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stage 6 Portfolio Financial Analytics Engine:
    Calculates total invested, current market value, realized P&L, unrealized P&L,
    overall return %, individual stock performance, and portfolio allocation using
    rigorous FIFO lot accounting.
    """
    transactions = _ensure_seed_transactions_for_user(db, current_user.id)
    fifo_data = compute_fifo_portfolio_holdings(transactions)
    return fifo_data


@router.get("/performance", response_model=PortfolioPerformanceResponse)
def get_portfolio_performance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns individual stock-by-stock performance metrics including realized
    and unrealized returns and portfolio weight.
    """
    transactions = _ensure_seed_transactions_for_user(db, current_user.id)
    fifo_data = compute_fifo_portfolio_holdings(transactions)

    return PortfolioPerformanceResponse(
        total_invested=fifo_data["total_invested"],
        current_portfolio_value=fifo_data["current_portfolio_value"],
        total_realized_pnl=fifo_data["realized_pnl"],
        total_unrealized_pnl=fifo_data["unrealized_pnl"],
        overall_return_percent=fifo_data["overall_return_percent"],
        performance=fifo_data["holdings"],
    )


@router.get("/allocation", response_model=PortfolioAllocationResponse)
def get_portfolio_allocation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns asset allocation breakdown by stock with exact percentage weights.
    """
    transactions = _ensure_seed_transactions_for_user(db, current_user.id)
    fifo_data = compute_fifo_portfolio_holdings(transactions)
    allocs = fifo_data["allocations"]

    top_sym = allocs[0]["symbol"] if allocs else None
    top_w = allocs[0]["weight_pct"] if allocs else 0.0

    return PortfolioAllocationResponse(
        total_portfolio_value=fifo_data["current_portfolio_value"],
        active_holdings_count=fifo_data["active_holdings_count"],
        allocations=allocs,
        top_holding_symbol=top_sym,
        top_holding_weight_pct=top_w,
    )


@router.get("/risk", response_model=PortfolioRiskResponse)
def get_portfolio_risk(
    period: str = Query("6mo", description="Historical lookback window: 1mo, 3mo, 6mo, 1y"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stage 6 Portfolio Risk Intelligence:
    Calculates top holding concentration, Herfindahl-Hirschman Index (HHI),
    weighted historical portfolio returns, annualized volatility, maximum drawdown,
    stock-wise volatilities, and benchmark beta against NIFTY 50.
    """
    transactions = _ensure_seed_transactions_for_user(db, current_user.id)
    fifo_data = compute_fifo_portfolio_holdings(transactions)
    active_holdings = [h for h in fifo_data["holdings"] if h["total_quantity"] > 0]

    risk_data = calculate_portfolio_risk(active_holdings, period=period)
    return risk_data


@router.get("/transactions", response_model=List[PortfolioTransactionResponse])
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all historical portfolio transactions for the authenticated user."""
    return db.query(PortfolioTransaction).filter(
        PortfolioTransaction.user_id == current_user.id
    ).order_by(PortfolioTransaction.transaction_date.desc(), PortfolioTransaction.id.desc()).all()


@router.post("/transaction", response_model=PortfolioTransactionResponse, status_code=status.HTTP_201_CREATED)
def add_transaction(
    data: PortfolioTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a buy or sell transaction to user's isolated portfolio."""
    norm_sym = normalize_symbol(data.symbol)
    q = get_stock_quote(norm_sym)

    tx = PortfolioTransaction(
        user_id=current_user.id,
        symbol=norm_sym,
        company_name=data.company_name or q.name,
        exchange=data.exchange,
        transaction_type=data.transaction_type.upper(),
        quantity=data.quantity,
        purchase_price=data.purchase_price,
        transaction_date=data.transaction_date,
        notes=data.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/transaction/{tx_id}")
def delete_transaction(
    tx_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a portfolio transaction belonging to user."""
    tx = db.query(PortfolioTransaction).filter(
        PortfolioTransaction.id == tx_id,
        PortfolioTransaction.user_id == current_user.id
    ).first()

    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    db.delete(tx)
    db.commit()
    return {"status": "success", "message": "Transaction deleted"}
