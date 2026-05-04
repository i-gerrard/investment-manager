"""
Real-time market price service backed by yfinance.

Prices are cached for CACHE_TTL_SECONDS to avoid hammering the upstream API
while keeping quotes fresh enough for CFD simulation purposes.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf

CACHE_TTL_SECONDS = 60

# ticker -> (price, fetched_at)
_cache: dict[str, tuple[float, datetime]] = {}


def _fetch_sync(ticker: str) -> float:
    """Blocking yfinance call — run in executor to keep async loop free."""
    info = yf.Ticker(ticker).fast_info
    price: Optional[float] = getattr(info, "last_price", None) or getattr(info, "previous_close", None)
    if price is None or price <= 0:
        raise ValueError(f"Cannot retrieve price for '{ticker}'")
    return float(price)


async def get_price(ticker: str) -> float:
    ticker = ticker.upper()
    cached = _cache.get(ticker)
    if cached:
        price, fetched_at = cached
        if datetime.utcnow() - fetched_at < timedelta(seconds=CACHE_TTL_SECONDS):
            return price

    loop = asyncio.get_event_loop()
    price = await loop.run_in_executor(None, _fetch_sync, ticker)
    _cache[ticker] = (price, datetime.utcnow())
    return price


async def get_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch multiple prices concurrently; silently skips any that fail."""
    results: dict[str, float] = {}
    tasks = {t: asyncio.create_task(get_price(t)) for t in tickers}
    for ticker, task in tasks.items():
        try:
            results[ticker] = await task
        except Exception:
            pass
    return results
