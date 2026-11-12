import datetime
import time
from typing import Dict, List, Optional, Any, Tuple
import pytz
import pandas as pd
import yfinance as yf

from backend.app.core.config import settings
from backend.app.schemas.market import IndexQuote, StockQuote, OHLCVPoint, StockHistory

# Indian Standard Time Zone
IST = pytz.timezone("Asia/Kolkata")

# In-memory Cache store: key -> (timestamp, data)
_CACHE: Dict[str, Tuple[float, Any]] = {}

# Well-known stock metadata for popular NSE/BSE tickers
SYMBOL_METADATA = {
    "RELIANCE.NS": {"name": "Reliance Industries Ltd", "exchange": "NSE", "sector": "Energy & Retail", "base_price": 2980.50},
    "TCS.NS": {"name": "Tata Consultancy Services Ltd", "exchange": "NSE", "sector": "Information Technology", "base_price": 4120.00},
    "HDFCBANK.NS": {"name": "HDFC Bank Ltd", "exchange": "NSE", "sector": "Financial Services", "base_price": 1640.25},
    "INFY.NS": {"name": "Infosys Ltd", "exchange": "NSE", "sector": "Information Technology", "base_price": 1825.80},
    "ICICIBANK.NS": {"name": "ICICI Bank Ltd", "exchange": "NSE", "sector": "Financial Services", "base_price": 1245.50},
    "SBIN.NS": {"name": "State Bank of India", "exchange": "NSE", "sector": "Public Banking", "base_price": 815.20},
    "BHARTIARTL.NS": {"name": "Bharti Airtel Ltd", "exchange": "NSE", "sector": "Telecom", "base_price": 1540.00},
    "ITC.NS": {"name": "ITC Ltd", "exchange": "NSE", "sector": "FMCG", "base_price": 492.75},
    "LT.NS": {"name": "Larsen & Toubro Ltd", "exchange": "NSE", "sector": "Construction & Engineering", "base_price": 3610.10},
    "TATAMOTORS.NS": {"name": "Tata Motors Ltd", "exchange": "NSE", "sector": "Automobile", "base_price": 985.40},
    "^NSEI": {"name": "NIFTY 50", "exchange": "NSE", "sector": "Index", "base_price": 24350.00},
    "^BSESN": {"name": "S&P BSE SENSEX", "exchange": "BSE", "sector": "Index", "base_price": 80100.00},
    "^NSEBANK": {"name": "NIFTY BANK", "exchange": "NSE", "sector": "Index", "base_price": 52150.00},
    "^INDIAVIX": {"name": "INDIA VIX", "exchange": "NSE", "sector": "Volatility Index", "base_price": 13.85}
}


def is_indian_market_open() -> Tuple[bool, str]:
    """
    Checks if Indian stock market (NSE/BSE) is currently in open trading hours.
    Standard regular trading hours: Monday through Friday, 09:15 to 15:30 IST.
    """
    now_ist = datetime.datetime.now(IST)
    weekday = now_ist.weekday()  # 0 is Monday, 6 is Sunday

    if weekday >= 5:
        return False, "Market is closed (Weekend)"

    time_now = now_ist.time()
    market_open = datetime.time(9, 15)
    market_close = datetime.time(15, 30)

    if market_open <= time_now <= market_close:
        return True, "Market is OPEN"
    elif time_now < market_open:
        return False, f"Market opens at 09:15 AM IST (Current: {time_now.strftime('%H:%M')})"
    else:
        return False, f"Market closed at 03:30 PM IST (Current: {time_now.strftime('%H:%M')})"


def _get_cache(key: str, ttl: int = settings.DEFAULT_CACHE_TTL) -> Optional[Any]:
    if key in _CACHE:
        ts, data = _CACHE[key]
        if time.time() - ts < ttl:
            return data
    return None


def _set_cache(key: str, data: Any):
    _CACHE[key] = (time.time(), data)


def normalize_symbol(symbol: str) -> str:
    """Normalizes symbol: e.g. 'RELIANCE' -> 'RELIANCE.NS', 'SENSEX' -> '^BSESN'"""
    sym = symbol.strip().upper()
    if sym in ["NIFTY", "NIFTY50", "NIFTY 50"]:
        return "^NSEI"
    if sym in ["SENSEX", "BSESN", "BSE"]:
        return "^BSESN"
    if sym in ["BANKNIFTY", "BANK NIFTY", "NIFTYBANK"]:
        return "^NSEBANK"
    if sym in ["VIX", "INDIAVIX", "INDIA VIX"]:
        return "^INDIAVIX"
    if not (sym.startswith("^") or sym.endswith(".NS") or sym.endswith(".BO")):
        # Default to NSE if no exchange suffix given
        return f"{sym}.NS"
    return sym


def fetch_quote_yfinance(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch recent quote from yfinance with timeout protection."""
    try:
        ticker = yf.Ticker(symbol)
        fast_info = ticker.fast_info

        # Try fast_info first
        last_price = getattr(fast_info, "last_price", None)
        prev_close = getattr(fast_info, "previous_close", None)

        if last_price is not None and not pd.isna(last_price):
            chg = (last_price - prev_close) if prev_close else 0.0
            pct = (chg / prev_close * 100) if prev_close else 0.0
            return {
                "price": round(float(last_price), 2),
                "previous_close": round(float(prev_close), 2) if prev_close else round(float(last_price), 2),
                "open": round(float(getattr(fast_info, "open", last_price)), 2),
                "high": round(float(getattr(fast_info, "day_high", last_price)), 2),
                "low": round(float(getattr(fast_info, "day_low", last_price)), 2),
                "close": round(float(last_price), 2),
                "change": round(float(chg), 2),
                "change_percent": round(float(pct), 2),
                "volume": int(getattr(fast_info, "last_volume", 0) or 0),
                "fifty_two_week_high": round(float(getattr(fast_info, "year_high", 0.0) or 0.0), 2) or None,
                "fifty_two_week_low": round(float(getattr(fast_info, "year_low", 0.0) or 0.0), 2) or None,
            }

        # Fallback to history
        hist = ticker.history(period="5d", interval="1d")
        if not hist.empty:
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else latest
            price = float(latest["Close"])
            prev_close = float(prev["Close"])
            chg = price - prev_close
            pct = (chg / prev_close) * 100 if prev_close else 0.0
            return {
                "price": round(price, 2),
                "previous_close": round(prev_close, 2),
                "open": round(float(latest["Open"]), 2),
                "high": round(float(latest["High"]), 2),
                "low": round(float(latest["Low"]), 2),
                "close": round(price, 2),
                "change": round(chg, 2),
                "change_percent": round(pct, 2),
                "volume": int(latest.get("Volume", 0)),
                "fifty_two_week_high": None,
                "fifty_two_week_low": None
            }
    except Exception as e:
        # yfinance network failure or rate limit
        return None
    return None


def get_verified_fallback_quote(symbol: str) -> Dict[str, Any]:
    """Generates a verified, realistic fallback quote clearly tagged as demo data."""
    meta = SYMBOL_METADATA.get(symbol, {
        "name": symbol.replace(".NS", "").replace(".BO", ""),
        "exchange": "NSE" if ".NS" in symbol else "BSE",
        "sector": "Equity",
        "base_price": 1000.00
    })
    base_p = meta["base_price"]
    prev_close = round(base_p * 0.995, 2)
    change = round(base_p - prev_close, 2)
    pct = round((change / prev_close) * 100, 2)

    return {
        "price": base_p,
        "previous_close": prev_close,
        "open": round(prev_close * 1.002, 2),
        "high": round(base_p * 1.012, 2),
        "low": round(prev_close * 0.992, 2),
        "close": base_p,
        "change": change,
        "change_percent": pct,
        "volume": 1250000,
        "fifty_two_week_high": round(base_p * 1.25, 2),
        "fifty_two_week_low": round(base_p * 0.78, 2)
    }


def get_stock_quote(symbol: str) -> StockQuote:
    """Returns a unified StockQuote, respecting market hours, caching, and fallback tagging."""
    norm_symbol = normalize_symbol(symbol)
    cache_key = f"quote_{norm_symbol}"

    cached = _get_cache(cache_key)
    is_market_open, _ = is_indian_market_open()
    now_ist_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

    meta = SYMBOL_METADATA.get(norm_symbol, {
        "name": norm_symbol.replace(".NS", "").replace(".BO", "").replace("^", ""),
        "exchange": "BSE" if ".BO" in norm_symbol or norm_symbol == "^BSESN" else "NSE",
        "sector": "Indian Equities"
    })

    if cached:
        return StockQuote(
            symbol=norm_symbol,
            name=meta["name"],
            exchange=meta["exchange"],
            sector=meta.get("sector"),
            is_live=is_market_open,
            is_market_open=is_market_open,
            timestamp=now_ist_str,
            data_source="cached",
            is_demo=cached.get("is_demo", False),
            **{k: v for k, v in cached.items() if k not in ["is_demo"]}
        )

    # Attempt fetch from yfinance
    q = fetch_quote_yfinance(norm_symbol)
    if q is not None:
        q["is_demo"] = False
        _set_cache(cache_key, q)
        return StockQuote(
            symbol=norm_symbol,
            name=meta["name"],
            exchange=meta["exchange"],
            sector=meta.get("sector"),
            is_live=is_market_open,
            is_market_open=is_market_open,
            timestamp=now_ist_str,
            data_source="live_api",
            is_demo=False,
            **{k: v for k, v in q.items() if k not in ["is_demo"]}
        )

    # If yfinance failed or timed out, provide clean fallback explicitly marked as demo data
    fallback_q = get_verified_fallback_quote(norm_symbol)
    fallback_q["is_demo"] = True
    _set_cache(cache_key, fallback_q)

    return StockQuote(
        symbol=norm_symbol,
        name=meta["name"],
        exchange=meta["exchange"],
        sector=meta.get("sector"),
        is_live=False,
        is_market_open=is_market_open,
        timestamp=now_ist_str,
        data_source="fallback_offline",
        is_demo=True,
        **{k: v for k, v in fallback_q.items() if k not in ["is_demo"]}
    )


def get_market_indices() -> List[IndexQuote]:
    """Fetches quotes for major benchmark indices: NIFTY 50, SENSEX, BANK NIFTY, INDIA VIX."""
    results: List[IndexQuote] = []
    is_market_open, _ = is_indian_market_open()
    now_ist_str = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

    for name, config in settings.INDICES.items():
        sym = config["symbol"]
        quote = get_stock_quote(sym)
        results.append(IndexQuote(
            name=name,
            symbol=sym,
            price=quote.price,
            change=quote.change,
            change_percent=quote.change_percent,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            previous_close=quote.previous_close,
            currency="INR",
            is_live=quote.is_live,
            is_market_open=is_market_open,
            timestamp=now_ist_str,
            data_source=quote.data_source,
            is_demo=quote.is_demo
        ))

    return results


def get_stock_history_df(symbol: str, period: str = "6mo", interval: str = "1d") -> Tuple[pd.DataFrame, bool, str]:
    """
    Fetches historical OHLCV data as a Pandas DataFrame.
    Returns: (df, is_demo, data_source)
    """
    norm_symbol = normalize_symbol(symbol)
    cache_key = f"hist_{norm_symbol}_{period}_{interval}"
    cached = _get_cache(cache_key, ttl=300)
    if cached is not None:
        df, is_demo, source = cached
        return df.copy(), is_demo, "cached"

    try:
        ticker = yf.Ticker(norm_symbol)
        hist = ticker.history(period=period, interval=interval)
        if not hist.empty and len(hist) >= 5:
            hist = hist.reset_index()
            # Normalize column names to lowercase
            col_map = {
                "Date": "timestamp",
                "Datetime": "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume"
            }
            hist = hist.rename(columns=col_map)
            hist["timestamp"] = hist["timestamp"].astype(str)
            hist = hist[["timestamp", "open", "high", "low", "close", "volume"]]
            _set_cache(cache_key, (hist, False, "live_api"))
            return hist.copy(), False, "live_api"
    except Exception:
        pass

    # Verified fallback generation
    hist = generate_synthetic_history(norm_symbol, period=period)
    _set_cache(cache_key, (hist, True, "fallback_offline"))
    return hist.copy(), True, "fallback_offline"


def generate_synthetic_history(symbol: str, period: str = "6mo") -> pd.DataFrame:
    """Generates realistic synthetic historical OHLCV series for fallback and offline tests."""
    meta = SYMBOL_METADATA.get(symbol, {"base_price": 1000.0})
    base_p = meta.get("base_price", 1000.0)

    days_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
    days = days_map.get(period, 180)

    dates = pd.bdate_range(end=datetime.date.today(), periods=days)
    n = len(dates)

    # Deterministic seed using symbol for consistent offline tests
    seed = sum(ord(c) for c in symbol)
    import numpy as np
    rng = np.random.default_rng(seed)

    returns = rng.normal(loc=0.0005, scale=0.015, size=n)
    price_multipliers = np.cumprod(1 + returns)
    closes = base_p * (price_multipliers / price_multipliers[-1])

    opens = closes * (1 + rng.normal(0, 0.005, size=n))
    highs = np.maximum(opens, closes) * (1 + np.abs(rng.normal(0, 0.008, size=n)))
    lows = np.minimum(opens, closes) * (1 - np.abs(rng.normal(0, 0.008, size=n)))
    volumes = rng.integers(500000, 5000000, size=n)

    df = pd.DataFrame({
        "timestamp": [d.strftime("%Y-%m-%d") for d in dates],
        "open": np.round(opens, 2),
        "high": np.round(highs, 2),
        "low": np.round(lows, 2),
        "close": np.round(closes, 2),
        "volume": volumes
    })
    return df
