import datetime
import pytz
from typing import List
from fastapi import APIRouter
from backend.app.schemas.market import MarketOverview, IndexQuote
from backend.app.services.market_service import (
    get_market_indices,
    is_indian_market_open,
    get_stock_quote,
    IST
)
from backend.app.core.config import settings

router = APIRouter()


@router.get("/overview", response_model=MarketOverview)
def get_overview():
    """Returns overview of Indian markets including major indices and trading status."""
    indices = get_market_indices()
    is_open, msg = is_indian_market_open()

    # Get sample top movers from default list
    top_movers = []
    for sym in settings.WATCHLIST_DEFAULTS[:5]:
        q = get_stock_quote(sym)
        top_movers.append({
            "symbol": q.symbol,
            "name": q.name,
            "price": q.price,
            "change": q.change,
            "change_percent": q.change_percent,
            "is_demo": q.is_demo
        })

    return MarketOverview(
        indices=indices,
        market_status="OPEN" if is_open else "CLOSED",
        market_message=msg,
        current_time_ist=datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        top_movers=top_movers
    )


@router.get("/indices", response_model=List[IndexQuote])
def get_indices():
    """Returns benchmark indices: NIFTY 50, SENSEX, BANK NIFTY, INDIA VIX."""
    return get_market_indices()

