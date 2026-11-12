from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.watchlist import WatchlistItem
from backend.app.schemas.watchlist import WatchlistCreate, WatchlistResponse
from backend.app.services.market_service import get_stock_quote, normalize_symbol, SYMBOL_METADATA

router = APIRouter()


@router.get("", response_model=List[WatchlistResponse])
def get_watchlist(db: Session = Depends(get_db)):
    """Fetches user watchlist enriched with latest quotes."""
    items = db.query(WatchlistItem).order_by(WatchlistItem.created_at.desc()).all()

    # If watchlist is empty, seed with initial popular stocks
    if not items:
        default_syms = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]
        for s in default_syms:
            meta = SYMBOL_METADATA.get(s, {"name": s, "exchange": "NSE"})
            item = WatchlistItem(
                user_id=1,
                symbol=s,
                company_name=meta.get("name"),
                exchange=meta.get("exchange", "NSE")
            )
            db.add(item)
        db.commit()
        items = db.query(WatchlistItem).all()

    results = []
    for it in items:
        q = get_stock_quote(it.symbol)
        results.append(WatchlistResponse(
            id=it.id,
            user_id=it.user_id,
            symbol=it.symbol,
            company_name=it.company_name or q.name,
            exchange=it.exchange,
            notes=it.notes,
            created_at=it.created_at,
            current_price=q.price,
            change=q.change,
            change_percent=q.change_percent
        ))
    return results


@router.post("", response_model=WatchlistResponse)
def add_to_watchlist(data: WatchlistCreate, db: Session = Depends(get_db)):
    """Adds a new stock to user watchlist."""
    norm_sym = normalize_symbol(data.symbol)

    existing = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == 1,
        WatchlistItem.symbol == norm_sym
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"{norm_sym} already exists in your watchlist")

    q = get_stock_quote(norm_sym)
    item = WatchlistItem(
        user_id=1,
        symbol=norm_sym,
        company_name=data.company_name or q.name,
        exchange=data.exchange or q.exchange,
        notes=data.notes
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return WatchlistResponse(
        id=item.id,
        user_id=item.user_id,
        symbol=item.symbol,
        company_name=item.company_name,
        exchange=item.exchange,
        notes=item.notes,
        created_at=item.created_at,
        current_price=q.price,
        change=q.change,
        change_percent=q.change_percent
    )


@router.delete("/{item_id}")
def delete_from_watchlist(item_id: int, db: Session = Depends(get_db)):
    """Removes a stock item from watchlist."""
    item = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    db.delete(item)
    db.commit()
    return {"status": "success", "message": f"Removed {item.symbol} from watchlist"}
