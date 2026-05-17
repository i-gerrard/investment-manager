"""Shared write path for daily portfolio snapshots.

Called by both broker_sync ingest and HTML report upload. Guarantees:
- one PortfolioSnapshot row per (user_id, report_date) — idempotent re-upload
- old holdings under that snapshot are wiped and re-inserted from the new payload
- ticker rows are created in `stocks` table on demand

market_value_usd is stored normalized to USD: TR (EUR) holdings are
converted using the snapshot's eur_usd_rate. When that rate is unknown
(e.g. broker_sync alone with no prior HTML upload), TR market_value_usd
is left NULL until a later writer enriches the rate.
avg_cost and current_price remain in the holding's native currency.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import Holding, PortfolioSnapshot
from app.services.report_parser import ParsedAccountSummary, ParsedHolding
from app.services.stock import StockService

logger = logging.getLogger(__name__)

_stock_service = StockService()


def _to_usd(h: ParsedHolding, eur_usd_rate: Optional[float]) -> Optional[float]:
    """Convert a parsed holding's market_value to USD.
    eToro (USD): pass-through. TR (EUR): multiply by rate, or None if rate unknown.
    """
    if h.market_value is None:
        return None
    if h.currency == "USD" or h.account == "etoro":
        return h.market_value
    if h.currency == "EUR" or h.account == "tr":
        if eur_usd_rate is None:
            return None
        return h.market_value * eur_usd_rate
    return h.market_value  # unknown currency: pass through


# ── Public API ───────────────────────────────────────────────────────────────

async def write_snapshot(
    db: AsyncSession,
    *,
    user_id: str,
    report_date: date,
    source: str,
    summary: ParsedAccountSummary,
    holdings: list[ParsedHolding],
    account_to_portfolio: dict[str, str],
    raw_html: Optional[str] = None,
    replace_accounts: Optional[set[str]] = None,
) -> PortfolioSnapshot:
    """Idempotent upsert of a portfolio snapshot + its holdings.

    Args:
        user_id: owner of the snapshot.
        report_date: snapshot calendar date; unique per user.
        source: 'broker_sync' | 'report_upload' | 'manual' — provenance tag.
        summary: parsed account-level totals (any field may be None).
        holdings: per-position rows; entries with account not in
            account_to_portfolio are skipped (with warning).
        account_to_portfolio: map {'etoro': portfolio_id, 'tr': portfolio_id, ...}
        raw_html: optional HTML backup; persisted only for source='report_upload'.
        replace_accounts: if provided, only wipe-and-replace holdings whose
            account is in this set (preserves other accounts on the same snapshot).
            Defaults to None → wipe ALL holdings under this snapshot. Use the
            set form for single-broker broker_sync ingests; the None form for
            full-portfolio HTML report uploads.

    Returns the persisted PortfolioSnapshot. Caller is responsible for the
    surrounding transaction commit if needed; this function does NOT commit.
    """
    if source not in {"broker_sync", "report_upload", "manual"}:
        raise ValueError(f"invalid source: {source!r}")

    snapshot = await _upsert_snapshot(
        db,
        user_id=user_id,
        report_date=report_date,
        source=source,
        summary=summary,
        raw_html=raw_html,
    )

    # Wipe old holdings — either everything under this snapshot or only the
    # accounts the caller is about to replace (so multi-broker scenarios where
    # each broker ingests separately don't clobber each other).
    wipe = delete(Holding).where(Holding.snapshot_id == snapshot.id)
    if replace_accounts is not None:
        wipe = wipe.where(Holding.account.in_(list(replace_accounts)))
    await db.execute(wipe)

    eur_usd = snapshot.eur_usd_rate  # may be None for broker_sync-only days

    # Pre-compute per-account total USD market value for position_percent.
    # Per-account share uses USD-normalized totals so % is comparable across
    # the snapshot.
    account_totals_usd: dict[str, float] = {}
    for h in holdings:
        mv_usd = _to_usd(h, eur_usd)
        if mv_usd is not None:
            account_totals_usd[h.account] = account_totals_usd.get(h.account, 0.0) + mv_usd

    skipped = 0
    for h in holdings:
        portfolio_id = account_to_portfolio.get(h.account)
        if not portfolio_id:
            logger.warning("Skip holding %s — no portfolio mapped for account %r",
                           h.ticker, h.account)
            skipped += 1
            continue

        stock = await _stock_service.ensure_stock(db, ticker=h.ticker, name=h.display_name)

        mv_usd = _to_usd(h, eur_usd)
        pct: Optional[float] = None
        total = account_totals_usd.get(h.account)
        if mv_usd is not None and total:
            pct = round(mv_usd / total * 100, 2)

        db.add(Holding(
            portfolio_id=portfolio_id,
            snapshot_id=snapshot.id,
            stock_id=stock.id,
            ticker=h.ticker,
            snapshot_date=report_date,
            account=h.account,
            shares=h.shares,
            avg_cost=h.avg_cost,  # native currency
            current_price=h.current_price,  # native currency
            market_value_usd=mv_usd,  # USD-normalized
            pnl_total_usd=None,  # not extracted in Phase B
            pnl_total_pct=h.pnl_total_pct,
            pnl_day_pct=h.pnl_day_pct,
            position_percent=pct,
        ))

    await db.flush()
    if skipped:
        logger.info("Snapshot %s: skipped %d holdings (no portfolio mapping)",
                    snapshot.id, skipped)
    return snapshot


# ── Internals ────────────────────────────────────────────────────────────────

async def _upsert_snapshot(
    db: AsyncSession,
    *,
    user_id: str,
    report_date: date,
    source: str,
    summary: ParsedAccountSummary,
    raw_html: Optional[str],
) -> PortfolioSnapshot:
    """Look up existing snapshot by (user_id, report_date); merge or create.

    On merge: non-None values in the new summary overwrite existing fields.
    Existing values remain when the new payload has nothing for that field —
    useful when a broker_sync ingest enriches an earlier report_upload row.
    """
    existing_q = select(PortfolioSnapshot).where(
        PortfolioSnapshot.user_id == user_id,
        PortfolioSnapshot.report_date == report_date,
    )
    snapshot = (await db.execute(existing_q)).scalar_one_or_none()

    if snapshot is None:
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            report_date=report_date,
            source=source,
            raw_html=raw_html if source == "report_upload" else None,
        )
        _apply_summary(snapshot, summary, overwrite=True)
        db.add(snapshot)
        await db.flush()
        return snapshot

    # Merge: only overwrite fields where the new summary provides a value.
    # Source is updated to reflect the latest writer.
    snapshot.source = source
    if source == "report_upload" and raw_html is not None:
        snapshot.raw_html = raw_html
    _apply_summary(snapshot, summary, overwrite=False)
    await db.flush()
    return snapshot


_SUMMARY_FIELDS = (
    "combined_total_usd", "combined_cash_usd", "cash_ratio_pct", "eur_usd_rate",
    "etoro_total_usd", "etoro_cash_usd", "etoro_invested_usd", "etoro_pnl_day_usd",
    "tr_total_eur", "tr_cash_eur", "tr_invested_eur", "tr_pnl_day_eur",
)


def _apply_summary(snapshot: PortfolioSnapshot, summary: ParsedAccountSummary,
                   *, overwrite: bool) -> None:
    for field_name in _SUMMARY_FIELDS:
        new_val = getattr(summary, field_name)
        if new_val is None and not overwrite:
            continue
        setattr(snapshot, field_name, new_val)
