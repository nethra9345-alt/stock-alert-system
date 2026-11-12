from typing import Dict
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.portfolio import PortfolioTransaction
from backend.app.schemas.portfolio import (
    PortfolioOverview,
    HoldingSummary,
    PortfolioTransactionCreate,
    PortfolioTransactionResponse
)
from backend.app.services.market_service import get_stock_quote, normalize_symbol, SYMBOL_METADATA

router = APIRouter()


@router.get("", response_model=PortfolioOverview)
def get_portfolio(db: Session = Depends(get_db)):
    """Computes aggregated portfolio metrics, positions, and live P&L."""
    transactions = db.query(PortfolioTransaction).all()

    # If empty, seed initial realistic portfolio for demonstration
    if not transactions:
        seed_data = [
            ("RELIANCE.NS", "BUY", 10, 2850.00, "Reliance Industries"),
            ("TCS.NS", "BUY", 5, 3950.00, "Tata Consultancy Services"),
            ("INFY.NS", "BUY", 20, 1720.00, "Infosys Ltd"),
            ("HDFCBANK.NS", "BUY", 15, 1580.00, "HDFC Bank Ltd")
        ]
        for sym, t_type, qty, price, name in seed_data:
            tx = PortfolioTransaction(
                user_id=1,
                symbol=sym,
                company_name=name,
                transaction_type=t_type,
                quantity=qty,
                purchase_price=price
            )
            db.add(tx)
        db.commit()
        transactions = db.query(PortfolioTransaction).all()

    # Aggregate holdings by symbol
    holdings_dict: Dict[str, Dict] = defaultdict(lambda: {
        "symbol": "",
        "company_name": "",
        "exchange": "NSE",
        "total_qty": 0.0,
        "total_cost": 0.0
    })

    for tx in transactions:
        sym = tx.symbol
        h = holdings_dict[sym]
        h["symbol"] = sym
        h["company_name"] = tx.company_name or h["company_name"]
        h["exchange"] = tx.exchange or "NSE"

        if tx.transaction_type.upper() == "BUY":
            h["total_qty"] += tx.quantity
            h["total_cost"] += (tx.quantity * tx.purchase_price)
        elif tx.transaction_type.upper() == "SELL":
            # Reduce quantity proportionally
            if h["total_qty"] > 0:
                avg_cost = h["total_cost"] / h["total_qty"]
                h["total_qty"] -= tx.quantity
                h["total_cost"] -= (tx.quantity * avg_cost)

    holdings_list = []
    total_invested = 0.0
    current_portfolio_value = 0.0

    for sym, h in holdings_dict.items():
        if h["total_qty"] <= 0:
            continue

        avg_price = h["total_cost"] / h["total_qty"] if h["total_qty"] > 0 else 0.0
        q = get_stock_quote(sym)
        curr_val = h["total_qty"] * q.price
        pnl = curr_val - h["total_cost"]
        pnl_pct = (pnl / h["total_cost"] * 100) if h["total_cost"] > 0 else 0.0

        total_invested += h["total_cost"]
        current_portfolio_value += curr_val

        holdings_list.append(HoldingSummary(
            symbol=sym,
            company_name=h["company_name"] or q.name,
            exchange=h["exchange"],
            total_quantity=round(h["total_qty"], 2),
            avg_buy_price=round(avg_price, 2),
            invested_value=round(h["total_cost"], 2),
            current_price=q.price,
            current_value=round(curr_val, 2),
            unrealized_pnl=round(pnl, 2),
            unrealized_pnl_percent=round(pnl_pct, 2)
        ))

    total_pnl = current_portfolio_value - total_invested
    total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    return PortfolioOverview(
        total_invested=round(total_invested, 2),
        current_portfolio_value=round(current_portfolio_value, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_percent=round(total_pnl_percent, 2),
        holdings_count=len(holdings_list),
        holdings=holdings_list
    )


@router.post("/transaction", response_model=PortfolioTransactionResponse)
def add_transaction(data: PortfolioTransactionCreate, db: Session = Depends(get_db)):
    """Adds a buy or sell transaction to user portfolio."""
    norm_sym = normalize_symbol(data.symbol)
    q = get_stock_quote(norm_sym)

    tx = PortfolioTransaction(
        user_id=1,
        symbol=norm_sym,
        company_name=data.company_name or q.name,
        exchange=data.exchange,
        transaction_type=data.transaction_type.upper(),
        quantity=data.quantity,
        purchase_price=data.purchase_price,
        notes=data.notes
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/transaction/{tx_id}")
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    """Deletes a portfolio transaction."""
    tx = db.query(PortfolioTransaction).filter(PortfolioTransaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
    return {"status": "success", "message": "Transaction deleted"}
