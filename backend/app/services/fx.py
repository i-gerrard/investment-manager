"""Foreign-exchange rate service.

Currently fetches USD/CNY from Bank of China's public 外汇牌价 page,
parsing the 美元 (USD) row and using the 中行折算价 (middle rate) column.
BoC quotes are CNY per 100 foreign units, so we divide by 100.

Cached in-process for `_TTL` seconds to be polite to BoC. Single-user
local app — no Redis / external cache needed.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BOC_URL = "https://www.boc.cn/sourcedb/whpj/"
_TTL = 600  # 10 minutes
_TIMEOUT = 10.0
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)


@dataclass
class FxRate:
    pair: str  # e.g. "USDCNY"
    rate: float  # 1 USD = rate CNY
    fetched_at: float  # epoch seconds
    published_at: Optional[str]  # source's own timestamp text
    source: str

    def to_dict(self) -> dict:
        return {
            "pair": self.pair,
            "rate": self.rate,
            "fetched_at": self.fetched_at,
            "published_at": self.published_at,
            "source": self.source,
        }


_cache: Optional[FxRate] = None
_lock = asyncio.Lock()


async def get_usd_cny(force_refresh: bool = False) -> FxRate:
    """Return the cached USD/CNY rate, refreshing from BoC if stale."""
    global _cache
    now = time.time()
    if (not force_refresh) and _cache and (now - _cache.fetched_at) < _TTL:
        return _cache

    async with _lock:
        # Double-check after acquiring lock
        if (not force_refresh) and _cache and (time.time() - _cache.fetched_at) < _TTL:
            return _cache
        rate = await _fetch_boc_usd_cny()
        _cache = rate
        return rate


async def _fetch_boc_usd_cny() -> FxRate:
    """Scrape BoC's 外汇牌价 page and pull out the USD middle-rate row."""
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as client:
        resp = await client.get(_BOC_URL)
        resp.raise_for_status()
        # BoC serves the page in GBK; httpx may guess wrong.
        if resp.encoding and resp.encoding.lower() != "utf-8":
            resp.encoding = "utf-8"
        html = resp.text

    soup = BeautifulSoup(html, "lxml")
    # The page has multiple tables; the rate table contains row headers like
    # 货币名称 / 现汇买入价 / 现钞买入价 / 现汇卖出价 / 现钞卖出价 / 中行折算价.
    target_row = None
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = rows[0].get_text(" ", strip=True)
        if "货币名称" not in header or "中行折算价" not in header:
            continue
        for r in rows[1:]:
            cells = r.find_all("td")
            if not cells:
                continue
            name = cells[0].get_text(strip=True)
            if name == "美元":
                target_row = cells
                break
        if target_row:
            break

    if not target_row or len(target_row) < 6:
        raise RuntimeError("BoC page did not contain USD row in expected layout")

    # Columns: 货币名称 / 现汇买入 / 现钞买入 / 现汇卖出 / 现钞卖出 / 中行折算价 / 发布时间
    mid_text = target_row[5].get_text(strip=True)
    try:
        mid_per100 = float(mid_text.replace(",", ""))
    except ValueError as exc:
        raise RuntimeError(f"BoC middle-rate not a number: {mid_text!r}") from exc

    published = target_row[6].get_text(strip=True) if len(target_row) >= 7 else None
    rate = mid_per100 / 100.0
    logger.info("BoC USD/CNY fetched: 1 USD = %.4f CNY (published %s)", rate, published)
    return FxRate(
        pair="USDCNY",
        rate=rate,
        fetched_at=time.time(),
        published_at=published,
        source="boc",
    )
