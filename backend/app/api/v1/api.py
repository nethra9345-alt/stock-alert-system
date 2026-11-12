from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    health,
    market,
    stocks,
    watchlist,
    portfolio,
    alerts
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(market.router, prefix="/market", tags=["Market"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["Stocks"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["Watchlist"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])

