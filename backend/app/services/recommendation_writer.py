"""Persist parsed recommendations as StockCard rows under a MorningReport.

Operates idempotently: existing standalone StockCards (those with
morning_report_id set and sector_recommendation_id == NULL) for the same
report are wiped before re-insertion.

Best-effort ticker extraction: the operations table cell typically reads
"<TICKER> <free text>" (e.g. "NVDA 财报"). Rows whose label doesn't start
with an uppercase ticker token are skipped with a warning. Multi-ticker
'(剩余)' summary rows are also skipped.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from sqlalchemy import and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import StockCard
from app.services.report_parser import ParsedRecommendation
from app.services.stock import StockService

logger = logging.getLogger(__name__)

_stock_service = StockService()

# Leading uppercase token (1-5 letters) followed by word boundary.
_TICKER_LEAD = re.compile(r"^([A-Z]{1,5})\b")
# Words that look like uppercase tokens but aren't tickers (account labels etc.)
_NOT_TICKERS = {"TR", "ETF", "ECB", "BOJ", "FOMC", "GDP", "CPI", "PPI"}


def _extract_ticker(label: str) -> Optional[str]:
    """Best-effort ticker extraction from a free-text recommendation label."""
    if not label:
        return None
    # Skip multi-ticker summary rows like "NVDA / GOOG / AAPL (剩余)"
    if "/" in label and label.count("/") >= 2:
        return None
    m = _TICKER_LEAD.match(label.strip())
    if not m:
        return None
    candidate = m.group(1)
    if candidate in _NOT_TICKERS:
        return None
    return candidate


async def persist_recommendations(
    db: AsyncSession,
    *,
    morning_report_id: str,
    report_date,
    recommendations: list[ParsedRecommendation],
) -> tuple[int, int]:
    """Wipe + re-insert standalone StockCards for this morning report.
    Returns (persisted_count, skipped_count).
    """
    await db.execute(
        delete(StockCard).where(and_(
            StockCard.morning_report_id == morning_report_id,
            StockCard.sector_recommendation_id.is_(None),
        ))
    )

    persisted = 0
    skipped = 0
    for r in recommendations:
        ticker = _extract_ticker(r.ticker_or_label)
        if not ticker:
            logger.warning("Skip recommendation, no ticker extracted: %r", r.ticker_or_label)
            skipped += 1
            continue

        stock = await _stock_service.ensure_stock(db, ticker=ticker, name=r.ticker_or_label)
        db.add(StockCard(
            morning_report_id=morning_report_id,
            sector_recommendation_id=None,
            stock_id=stock.id,
            direction=r.direction or "wait",
            priority=r.priority_raw,
            account=r.account,
            reference_price=r.reference_price,
            report_date=report_date,
            logic_analysis=r.rationale,
            operation_advice=r.trigger_text,
        ))
        persisted += 1

    await db.flush()
    return persisted, skipped
