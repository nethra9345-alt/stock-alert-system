"""Portfolio Analytics Engine with FIFO Cost Basis Accounting.

Accounting Methodology:
- First-In, First-Out (FIFO) is applied to all BUY and SELL transactions chronologically.
- Each BUY creates an open lot (quantity, purchase_price, transaction_date).
- Each SELL consumes open lots in FIFO order:
    Realized P&L = Sum(Lot_Qty_Sold * (Sell_Price - Lot_Buy_Price))
- Remaining open lots define the cost basis for active holdings:
    Invested Value = Sum(Open_Lot_Qty * Open_Lot_Price)
    Avg Buy Price = Invested Value / Total Open Quantity
- Unrealized P&L = Current Value - Invested Value
- Total P&L = Total Realized P&L + Total Unrealized P&L
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from collections import defaultdict
import math

from backend.app.models.portfolio import PortfolioTransaction
from backend.app.services.market_service import get_stock_quote


class FIFOLot:
    def __init__(self, quantity: float, purchase_price: float, transaction_date: datetime, tx_id: int):
        self.quantity = float(quantity)
        self.purchase_price = float(purchase_price)
        self.transaction_date = transaction_date
        self.tx_id = tx_id


def compute_fifo_portfolio_holdings(
    transactions: List[PortfolioTransaction],
    quote_price_map: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Computes holding positions, realized P&L, unrealized P&L, and asset allocations
    using deterministic FIFO lot matching.
    """
    # Sort transactions chronologically: earliest date first, then by transaction id
    sorted_txs = sorted(
        transactions,
        key=lambda tx: (tx.transaction_date or datetime.min, tx.id or 0)
    )

    open_lots_by_symbol: Dict[str, List[FIFOLot]] = defaultdict(list)
    realized_pnl_by_symbol: Dict[str, float] = defaultdict(float)
    closed_cost_basis_by_symbol: Dict[str, float] = defaultdict(float)
    company_names: Dict[str, str] = {}
    exchanges: Dict[str, str] = {}

    for tx in sorted_txs:
        sym = tx.symbol.upper()
        if tx.company_name:
            company_names[sym] = tx.company_name
        if tx.exchange:
            exchanges[sym] = tx.exchange

        tx_type = tx.transaction_type.upper().strip()
        qty = float(tx.quantity)
        price = float(tx.purchase_price)

        if tx_type == "BUY":
            open_lots_by_symbol[sym].append(
                FIFOLot(
                    quantity=qty,
                    purchase_price=price,
                    transaction_date=tx.transaction_date or datetime.utcnow(),
                    tx_id=tx.id or 0,
                )
            )
        elif tx_type == "SELL":
            remaining_sell_qty = qty
            lots = open_lots_by_symbol[sym]

            while remaining_sell_qty > 0 and lots:
                earliest_lot = lots[0]
                if earliest_lot.quantity <= remaining_sell_qty:
                    # Fully consume this lot
                    lot_qty = earliest_lot.quantity
                    cost_basis = lot_qty * earliest_lot.purchase_price
                    proceeds = lot_qty * price
                    realized_pnl_by_symbol[sym] += (proceeds - cost_basis)
                    closed_cost_basis_by_symbol[sym] += cost_basis
                    remaining_sell_qty -= lot_qty
                    lots.pop(0)
                else:
                    # Partially consume this lot
                    cost_basis = remaining_sell_qty * earliest_lot.purchase_price
                    proceeds = remaining_sell_qty * price
                    realized_pnl_by_symbol[sym] += (proceeds - cost_basis)
                    closed_cost_basis_by_symbol[sym] += cost_basis
                    earliest_lot.quantity -= remaining_sell_qty
                    remaining_sell_qty = 0.0

            # Edge case: oversold / short sale without prior buy
            if remaining_sell_qty > 0:
                # Lot exhausted; record unmatched quantity
                closed_cost_basis_by_symbol[sym] += remaining_sell_qty * price

    # Build active holdings from open lots
    holdings_result = []
    total_invested = 0.0
    current_portfolio_value = 0.0
    total_realized_pnl = sum(realized_pnl_by_symbol.values())
    total_closed_cost = sum(closed_cost_basis_by_symbol.values())

    # Collect symbols that have open lots OR realized P&L
    all_symbols = set(open_lots_by_symbol.keys()) | set(realized_pnl_by_symbol.keys())

    for sym in sorted(all_symbols):
        lots = open_lots_by_symbol.get(sym, [])
        open_qty = sum(lot.quantity for lot in lots)
        invested_cost = sum(lot.quantity * lot.purchase_price for lot in lots)
        realized_sym_pnl = realized_pnl_by_symbol.get(sym, 0.0)

        # Get current price
        if quote_price_map and sym in quote_price_map:
            current_price = quote_price_map[sym]
            comp_name = company_names.get(sym, sym)
        else:
            try:
                q = get_stock_quote(sym)
                current_price = q.price
                comp_name = company_names.get(sym, q.name)
            except Exception:
                current_price = invested_cost / open_qty if open_qty > 0 else 0.0
                comp_name = company_names.get(sym, sym)

        if open_qty > 0:
            avg_buy_price = invested_cost / open_qty
            curr_val = open_qty * current_price
            unrealized = curr_val - invested_cost
            unrealized_pct = (unrealized / invested_cost * 100.0) if invested_cost > 0 else 0.0

            total_invested += invested_cost
            current_portfolio_value += curr_val

            holdings_result.append({
                "symbol": sym,
                "company_name": comp_name,
                "exchange": exchanges.get(sym, "NSE"),
                "total_quantity": round(open_qty, 4),
                "avg_buy_price": round(avg_buy_price, 2),
                "invested_value": round(invested_cost, 2),
                "current_price": round(current_price, 2),
                "current_value": round(curr_val, 2),
                "unrealized_pnl": round(unrealized, 2),
                "unrealized_pnl_percent": round(unrealized_pct, 2),
                "realized_pnl": round(realized_sym_pnl, 2),
                "portfolio_weight_pct": 0.0,  # Will normalize below
            })
        elif realized_sym_pnl != 0.0:
            # Completely closed position with realized P&L
            holdings_result.append({
                "symbol": sym,
                "company_name": comp_name,
                "exchange": exchanges.get(sym, "NSE"),
                "total_quantity": 0.0,
                "avg_buy_price": 0.0,
                "invested_value": 0.0,
                "current_price": round(current_price, 2),
                "current_value": 0.0,
                "unrealized_pnl": 0.0,
                "unrealized_pnl_percent": 0.0,
                "realized_pnl": round(realized_sym_pnl, 2),
                "portfolio_weight_pct": 0.0,
            })

    # Compute portfolio weights for active holdings
    active_holdings = [h for h in holdings_result if h["total_quantity"] > 0]
    for h in active_holdings:
        if current_portfolio_value > 0:
            h["portfolio_weight_pct"] = round((h["current_value"] / current_portfolio_value) * 100.0, 2)
        else:
            h["portfolio_weight_pct"] = round(100.0 / len(active_holdings), 2)

    total_unrealized_pnl = current_portfolio_value - total_invested
    total_pnl = total_unrealized_pnl + total_realized_pnl

    # Overall return percentage:
    # If active invested exists, relative to total invested; if all closed, relative to closed cost basis
    cost_base = total_invested + total_closed_cost
    if cost_base > 0:
        overall_return_pct = (total_pnl / cost_base) * 100.0
    elif total_invested > 0:
        overall_return_pct = (total_unrealized_pnl / total_invested) * 100.0
    else:
        overall_return_pct = 0.0

    # Build asset allocation list (sorted descending by weight)
    allocations = []
    for h in sorted(active_holdings, key=lambda x: x["current_value"], reverse=True):
        allocations.append({
            "symbol": h["symbol"],
            "company_name": h["company_name"],
            "current_value": h["current_value"],
            "weight_pct": h["portfolio_weight_pct"],
        })

    return {
        "accounting_methodology": "FIFO (First-In, First-Out)",
        "total_invested": round(total_invested, 2),
        "current_portfolio_value": round(current_portfolio_value, 2),
        "realized_pnl": round(total_realized_pnl, 2),
        "unrealized_pnl": round(total_unrealized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "overall_return_percent": round(overall_return_pct, 2),
        "active_holdings_count": len(active_holdings),
        "holdings": holdings_result,
        "allocations": allocations,
    }
