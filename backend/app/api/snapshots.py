"""Snapshot query API — read-only endpoints over portfolio_snapshots
and the associated holdings. Write path lives in services/snapshot_writer.py.
"""

from datetime import date as Date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.portfolio import Holding, PortfolioSnapshot
from app.models.user import User
from app.schemas.snapshot import (
    HoldingDiff,
    HoldingHistoryPoint,
    HoldingSnapshotRow,
    PortfolioSummaryPoint,
    SnapshotCompare,
    SnapshotDetail,
    SnapshotListItem,
)

router = APIRouter(prefix="/api/v1", tags=["snapshots"])


# ── Snapshot list / detail ──

@router.get("/snapshots", response_model=list[SnapshotListItem])
async def list_snapshots(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: Optional[Date] = Query(None, alias="from"),
    to_date: Optional[Date] = Query(None, alias="to"),
    limit: int = Query(60, ge=1, le=365),
):
    """List snapshot dates for the current user, newest first."""
    q = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == current_user.id)
    if from_date:
        q = q.where(PortfolioSnapshot.report_date >= from_date)
    if to_date:
        q = q.where(PortfolioSnapshot.report_date <= to_date)
    q = q.order_by(PortfolioSnapshot.report_date.desc()).limit(limit)

    snaps = (await db.execute(q)).scalars().all()
    counts = await _count_holdings([s.id for s in snaps], db)
    return [
        SnapshotListItem(
            id=s.id, report_date=s.report_date, source=s.source,
            combined_total_usd=s.combined_total_usd,
            combined_cash_usd=s.combined_cash_usd,
            cash_ratio_pct=s.cash_ratio_pct,
            holdings_count=counts.get(s.id, 0),
            created_at=s.created_at,
        )
        for s in snaps
    ]


# Note: /snapshots/compare MUST be declared before /snapshots/{snap_date}
# so the literal path wins over the date path parameter.

@router.get("/snapshots/compare", response_model=SnapshotCompare)
async def compare_snapshots(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: Date = Query(..., alias="from"),
    to_date: Date = Query(..., alias="to"),
):
    s_from = await _get_snapshot_or_404(db, current_user.id, from_date)
    s_to = await _get_snapshot_or_404(db, current_user.id, to_date)

    h_from = (await db.execute(
        select(Holding).where(Holding.snapshot_id == s_from.id)
    )).scalars().all()
    h_to = (await db.execute(
        select(Holding).where(Holding.snapshot_id == s_to.id)
    )).scalars().all()

    diffs = _diff_holdings(h_from, h_to)

    return SnapshotCompare(
        from_date=from_date,
        to_date=to_date,
        from_total_usd=s_from.combined_total_usd,
        to_total_usd=s_to.combined_total_usd,
        total_delta_usd=_delta(s_to.combined_total_usd, s_from.combined_total_usd),
        from_cash_usd=s_from.combined_cash_usd,
        to_cash_usd=s_to.combined_cash_usd,
        cash_delta_usd=_delta(s_to.combined_cash_usd, s_from.combined_cash_usd),
        holdings=diffs,
    )


@router.get("/snapshots/{snap_date}", response_model=SnapshotDetail)
async def get_snapshot(
    snap_date: Date,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    snap = await _get_snapshot_or_404(db, current_user.id, snap_date)
    count = (await _count_holdings([snap.id], db)).get(snap.id, 0)
    return SnapshotDetail.model_validate({**snap.__dict__, "holdings_count": count})


@router.get("/snapshots/{snap_date}/holdings", response_model=list[HoldingSnapshotRow])
async def get_snapshot_holdings(
    snap_date: Date,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    account: Optional[str] = Query(None, pattern="^(etoro|tr|manual)$"),
):
    snap = await _get_snapshot_or_404(db, current_user.id, snap_date)
    q = select(Holding).where(Holding.snapshot_id == snap.id)
    if account:
        q = q.where(Holding.account == account)
    q = q.order_by(Holding.market_value_usd.desc().nulls_last())
    rows = (await db.execute(q)).scalars().all()
    return [HoldingSnapshotRow.model_validate(h) for h in rows]


# ── Per-ticker history ──

@router.get("/holdings/{ticker}/history", response_model=list[HoldingHistoryPoint])
async def holding_history(
    ticker: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    account: Optional[str] = Query(None, pattern="^(etoro|tr|manual)$"),
    limit: int = Query(180, ge=1, le=730),
):
    """Time series for one ticker across all snapshots owned by the user.
    Useful for the per-stock chart on the snapshot detail page.
    """
    q = (
        select(Holding)
        .join(PortfolioSnapshot, Holding.snapshot_id == PortfolioSnapshot.id)
        .where(PortfolioSnapshot.user_id == current_user.id)
        .where(Holding.ticker == ticker.upper())
    )
    if account:
        q = q.where(Holding.account == account)
    q = q.order_by(Holding.snapshot_date.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    # Return chronological (oldest first) for chart plotting
    rows = sorted(rows, key=lambda h: h.snapshot_date or Date.min)
    return [
        HoldingHistoryPoint(
            report_date=h.snapshot_date,
            account=h.account,
            shares=h.shares,
            avg_cost=h.avg_cost,
            current_price=h.current_price,
            market_value_usd=h.market_value_usd,
            pnl_total_pct=h.pnl_total_pct,
        )
        for h in rows
        if h.snapshot_date is not None
    ]


# ── Portfolio-level summary trend (for dashboard chart) ──

@router.get("/portfolio/summary", response_model=list[PortfolioSummaryPoint])
async def portfolio_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(90, ge=1, le=730),
):
    q = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == current_user.id)
        .order_by(PortfolioSnapshot.report_date.desc())
        .limit(days)
    )
    snaps = (await db.execute(q)).scalars().all()
    snaps = sorted(snaps, key=lambda s: s.report_date)
    return [
        PortfolioSummaryPoint(
            report_date=s.report_date,
            combined_total_usd=s.combined_total_usd,
            combined_cash_usd=s.combined_cash_usd,
            cash_ratio_pct=s.cash_ratio_pct,
            etoro_total_usd=s.etoro_total_usd,
            tr_total_eur=s.tr_total_eur,
        )
        for s in snaps
    ]


# ── Helpers ──

async def _get_snapshot_or_404(db: AsyncSession, user_id: str, snap_date: Date) -> PortfolioSnapshot:
    snap = (await db.execute(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.report_date == snap_date,
        )
    )).scalar_one_or_none()
    if not snap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No snapshot for {snap_date}")
    return snap


async def _count_holdings(snapshot_ids: list[str], db: AsyncSession) -> dict[str, int]:
    if not snapshot_ids:
        return {}
    rows = (await db.execute(
        select(Holding.snapshot_id, func.count(Holding.id))
        .where(Holding.snapshot_id.in_(snapshot_ids))
        .group_by(Holding.snapshot_id)
    )).all()
    return {sid: cnt for sid, cnt in rows}


def _delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return a - b


def _diff_holdings(h_from: list[Holding], h_to: list[Holding]) -> list[HoldingDiff]:
    """Diff two holdings lists keyed by (account, ticker)."""
    key = lambda h: (h.account or "", h.ticker)
    m_from = {key(h): h for h in h_from}
    m_to = {key(h): h for h in h_to}
    all_keys = sorted(set(m_from) | set(m_to))

    diffs: list[HoldingDiff] = []
    for k in all_keys:
        a = m_from.get(k)
        b = m_to.get(k)
        if a is None:
            change_type = "added"
        elif b is None:
            change_type = "removed"
        elif (a.shares or 0) != (b.shares or 0):
            change_type = "changed"
        else:
            change_type = "unchanged"

        diffs.append(HoldingDiff(
            ticker=k[1],
            account=k[0] or None,
            change_type=change_type,
            from_shares=a.shares if a else None,
            to_shares=b.shares if b else None,
            shares_delta=_delta(b.shares if b else None, a.shares if a else None),
            from_market_value_usd=a.market_value_usd if a else None,
            to_market_value_usd=b.market_value_usd if b else None,
            value_delta_usd=_delta(b.market_value_usd if b else None,
                                    a.market_value_usd if a else None),
            from_pnl_pct=a.pnl_total_pct if a else None,
            to_pnl_pct=b.pnl_total_pct if b else None,
        ))
    return diffs
