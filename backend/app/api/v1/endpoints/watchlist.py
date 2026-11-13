from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User
from backend.app.models.watchlist import WatchlistItem
from backend.app.schemas.watchlist import WatchlistCreate, WatchlistUpdate, WatchlistResponse
from backend.app.services.market_service import get_stock_quote, normalize_symbol, SYMBOL_METADATA

router = APIRouter()


@router.get("", response_model=List[WatchlistResponse])
def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches user watchlist strictly isolated to the authenticated user."""
    items = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == current_user.id
    ).order_by(WatchlistItem.created_at.desc()).all()

    # If primary user's watchlist is empty, seed with initial popular stocks (dev/demo only)
    if not items and current_user.id == 1 and settings.is_demo_allowed:
        default_syms = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]
        for s in default_syms:
            meta = SYMBOL_METADATA.get(s, {"name": s, "exchange": "NSE"})
            item = WatchlistItem(
                user_id=current_user.id,
                symbol=s,
                company_name=meta.get("name"),
                exchange=meta.get("exchange", "NSE")
            )
            db.add(item)
        db.commit()
        items = db.query(WatchlistItem).filter(WatchlistItem.user_id == current_user.id).all()

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


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    data: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a new stock to the authenticated user's isolated watchlist."""
    norm_sym = normalize_symbol(data.symbol)

    existing = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == current_user.id,
        WatchlistItem.symbol == norm_sym
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{norm_sym} already exists in your watchlist"
        )

    q = get_stock_quote(norm_sym)
    item = WatchlistItem(
        user_id=current_user.id,
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


@router.put("/{item_id}", response_model=WatchlistResponse)
def update_watchlist_item(
    item_id: int,
    data: WatchlistUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates notes or details of an existing watchlist item owned by user."""
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found")

    if data.notes is not None:
        item.notes = data.notes
    if data.company_name is not None:
        item.company_name = data.company_name

    db.commit()
    db.refresh(item)
    q = get_stock_quote(item.symbol)

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
def delete_from_watchlist(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Removes a stock item from user's isolated watchlist."""
    item = db.query(WatchlistItem).filter(
        WatchlistItem.id == item_id,
        WatchlistItem.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist item not found")

    sym = item.symbol
    db.delete(item)
    db.commit()
    return {"status": "success", "message": f"Removed {sym} from watchlist"}
