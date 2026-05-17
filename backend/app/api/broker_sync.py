"""
Broker sync module: receives positions from the sync script and exposes
dashboard/status endpoints.

Data flow:
  scripts/sync_brokers.py  →  POST /ingest  →  updates Holdings in DB
  frontend "Sync" button   →  POST /trigger →  spawns sync script subprocess
  frontend status poll     →  GET  /status  →  last sync logs
"""

import asyncio
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.broker_sync import BrokerPortfolioMapping, BrokerSyncLog
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.broker_sync import (
    BrokerIngestRequest,
    BrokerPortfolioMappingCreate,
    BrokerPortfolioMappingResponse,
    BrokerSyncLogResponse,
    BrokerSyncStatusResponse,
)
from app.services.report_parser import ParsedAccountSummary, ParsedHolding
from app.services.snapshot_writer import write_snapshot

router = APIRouter(prefix="/api/v1/broker-sync", tags=["broker-sync"])

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_mapping(broker: str, user_id: str, db: AsyncSession) -> Optional[BrokerPortfolioMapping]:
    result = await db.execute(
        select(BrokerPortfolioMapping).where(
            BrokerPortfolioMapping.broker == broker,
            BrokerPortfolioMapping.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _last_log(broker: str, db: AsyncSession) -> Optional[BrokerSyncLog]:
    result = await db.execute(
        select(BrokerSyncLog)
        .where(BrokerSyncLog.broker == broker)
        .order_by(BrokerSyncLog.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _build_account_summary(broker: str, positions: list) -> ParsedAccountSummary:
    """Derive minimal account-level totals from a single broker's positions.

    Broker_sync only captures positions, not cash/total/rate, so most snapshot
    summary fields are left None. The HTML report upload path enriches the
    same snapshot when both run on the same day.
    """
    invested = sum(p.market_value for p in positions if p.market_value is not None)
    summary = ParsedAccountSummary()
    if broker == "etoro":
        summary.etoro_invested_usd = invested or None
    elif broker == "tr":
        summary.tr_invested_eur = invested or None
    return summary


def _broker_positions_to_holdings(broker: str, positions: list) -> list[ParsedHolding]:
    currency = "USD" if broker == "etoro" else "EUR"
    return [
        ParsedHolding(
            account=broker,
            ticker=p.ticker.upper(),
            display_name=p.name or p.ticker,
            currency=currency,
            shares=p.quantity,
            avg_cost=p.avg_cost or p.current_price,
            current_price=p.current_price,
            market_value=p.market_value,
            pnl_total_pct=p.pnl_pct,
            pnl_day_pct=None,
        )
        for p in positions
    ]


# ── Portfolio mapping ─────────────────────────────────────────────────────────

@router.get("/mappings", response_model=list[BrokerPortfolioMappingResponse])
async def list_mappings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BrokerPortfolioMapping).where(BrokerPortfolioMapping.user_id == user.id)
    )
    rows = result.scalars().all()
    return [
        BrokerPortfolioMappingResponse(
            id=r.id,
            broker=r.broker,
            portfolio_id=r.portfolio_id,
            portfolio_name=r.portfolio.name if r.portfolio else None,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/mappings", response_model=BrokerPortfolioMappingResponse, status_code=201)
async def upsert_mapping(
    body: BrokerPortfolioMappingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify portfolio belongs to user
    p_result = await db.execute(
        select(Portfolio).where(Portfolio.id == body.portfolio_id, Portfolio.user_id == user.id)
    )
    if not p_result.scalar_one_or_none():
        raise HTTPException(404, "Portfolio not found")

    existing = await _get_mapping(body.broker, user.id, db)
    if existing:
        existing.portfolio_id = body.portfolio_id
        mapping = existing
    else:
        mapping = BrokerPortfolioMapping(
            user_id=user.id,
            broker=body.broker,
            portfolio_id=body.portfolio_id,
        )
        db.add(mapping)

    await db.commit()
    await db.refresh(mapping)
    return BrokerPortfolioMappingResponse(
        id=mapping.id,
        broker=mapping.broker,
        portfolio_id=mapping.portfolio_id,
        portfolio_name=mapping.portfolio.name if mapping.portfolio else None,
        created_at=mapping.created_at,
    )


# ── Ingest (called by sync script) ───────────────────────────────────────────

@router.post("/ingest", response_model=BrokerSyncLogResponse)
async def ingest_positions(
    body: BrokerIngestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Receive scraped positions from sync_brokers.py and persist as today's
    snapshot. Uses snapshot_writer so HTML report uploads on the same date
    can enrich the same row.
    """
    log = BrokerSyncLog(
        broker=body.broker,
        status="running",
        positions_read=len(body.positions),
        raw_snapshot=json.dumps([p.model_dump() for p in body.positions]),
    )
    db.add(log)
    await db.flush()

    # Resolve target portfolio
    portfolio_id = body.portfolio_id
    if not portfolio_id:
        mapping = await _get_mapping(body.broker, user.id, db)
        portfolio_id = mapping.portfolio_id if mapping else None

    if not portfolio_id:
        log.status = "failed"
        log.error_msg = "No portfolio mapping configured for this broker"
        log.finished_at = datetime.now(timezone.utc)
        await db.commit()
        raise HTTPException(422, log.error_msg)

    log.portfolio_id = portfolio_id

    try:
        snapshot = await write_snapshot(
            db,
            user_id=user.id,
            report_date=date.today(),
            source="broker_sync",
            summary=_build_account_summary(body.broker, body.positions),
            holdings=_broker_positions_to_holdings(body.broker, body.positions),
            account_to_portfolio={body.broker: portfolio_id},
            replace_accounts={body.broker},  # don't clobber the other broker's holdings
        )
        log.positions_synced = len(body.positions)
        log.status = "success"
    except Exception as exc:
        log.status = "failed"
        log.error_msg = str(exc)

    log.finished_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(log)
    return BrokerSyncLogResponse.model_validate(log)


# ── Trigger ───────────────────────────────────────────────────────────────────

@router.post("/trigger")
async def trigger_sync(
    broker: str = Query("all", pattern="^(etoro|tr|all)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Spawn sync_brokers.py as a background subprocess.
    Returns immediately; poll /status to track progress.
    """
    script = SCRIPTS_DIR / "sync_brokers.py"
    if not script.exists():
        raise HTTPException(500, f"Sync script not found at {script}")

    log = BrokerSyncLog(broker=broker, status="running")
    db.add(log)
    await db.commit()
    await db.refresh(log)

    env = os.environ.copy()
    env["BROKER_SYNC_USER_ID"] = user.id
    env["BROKER_SYNC_BROKER"] = broker

    async def _run():
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script),
            "--broker", broker,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    asyncio.create_task(_run())
    return {"job_id": log.id, "status": "running", "message": "Sync started"}


# ── Status & logs ─────────────────────────────────────────────────────────────

@router.get("/status", response_model=BrokerSyncStatusResponse)
async def get_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    etoro_log = await _last_log("etoro", db)
    tr_log = await _last_log("tr", db)
    etoro_map = await _get_mapping("etoro", user.id, db)
    tr_map = await _get_mapping("tr", user.id, db)

    def _map_resp(m: Optional[BrokerPortfolioMapping]):
        if not m:
            return None
        return BrokerPortfolioMappingResponse(
            id=m.id,
            broker=m.broker,
            portfolio_id=m.portfolio_id,
            portfolio_name=m.portfolio.name if m.portfolio else None,
            created_at=m.created_at,
        )

    return BrokerSyncStatusResponse(
        etoro_last_sync=BrokerSyncLogResponse.model_validate(etoro_log) if etoro_log else None,
        tr_last_sync=BrokerSyncLogResponse.model_validate(tr_log) if tr_log else None,
        etoro_mapping=_map_resp(etoro_map),
        tr_mapping=_map_resp(tr_map),
    )


@router.get("/logs", response_model=list[BrokerSyncLogResponse])
async def list_logs(
    broker: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(BrokerSyncLog)
        .order_by(BrokerSyncLog.started_at.desc())
        .limit(limit)
    )
    if broker:
        stmt = stmt.where(BrokerSyncLog.broker == broker)
    result = await db.execute(stmt)
    return [BrokerSyncLogResponse.model_validate(r) for r in result.scalars().all()]
