"""Trade-review API: recommendations, executions, simulations, aggregates.

Recommendations are StockCard rows (extended in Phase A). Each can have
multiple Execution rows (typically 1) and multiple Simulation rows.

All routes scope to the current user via the morning_report → user_id
chain. Since the system is single-user in practice, we don't store user_id
directly on StockCard; user filtering happens through join to MorningReport
when needed, but for simplicity all reads are global to authenticated user.
"""

from datetime import date as Date, datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.report import StockCard
from app.models.review import Execution, Simulation
from app.models.user import User
from app.schemas.review import (
    ExecutionCreate,
    ExecutionRead,
    RecommendationDetail,
    RecommendationListItem,
    RegretItem,
    ReviewStats,
    SimulationCreate,
    SimulationRead,
    SkipCreate,
    StockBrief,
)

router = APIRouter(prefix="/api/v1", tags=["review"])


# ── Recommendations ──

@router.get("/recommendations", response_model=list[RecommendationListItem])
async def list_recommendations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: Optional[Date] = Query(None, alias="from"),
    to_date: Optional[Date] = Query(None, alias="to"),
    ticker: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status",
                                          pattern="^(executed|skipped|partial|pending)$"),
    limit: int = Query(100, ge=1, le=500),
):
    """List recommendations, newest first. Filterable by date range,
    ticker, and execution status.
    """
    q = select(StockCard).options(
        selectinload(StockCard.stock),
        selectinload(StockCard.executions),
    )
    if from_date:
        q = q.where(StockCard.report_date >= from_date)
    if to_date:
        q = q.where(StockCard.report_date <= to_date)
    if ticker:
        q = q.where(StockCard.stock.has(ticker=ticker.upper()))
    q = q.order_by(StockCard.report_date.desc().nulls_last(),
                   StockCard.created_at.desc()).limit(limit)

    rows = (await db.execute(q)).scalars().all()
    items = []
    for r in rows:
        exec_status = r.executions[0].status if r.executions else None
        if status_filter == "pending" and exec_status is not None:
            continue
        if status_filter and status_filter != "pending" and exec_status != status_filter:
            continue
        items.append(RecommendationListItem(
            id=r.id, ticker=r.stock.ticker if r.stock else "?",
            direction=r.direction, priority=r.priority, account=r.account,
            reference_price=r.reference_price, report_date=r.report_date,
            operation_advice=r.operation_advice,
            has_execution=bool(r.executions),
            execution_status=exec_status,
            stock=StockBrief.model_validate(r.stock) if r.stock else None,
        ))
    return items


@router.get("/recommendations/{rec_id}", response_model=RecommendationDetail)
async def get_recommendation(
    rec_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rec = await _get_rec_or_404(db, rec_id)
    return RecommendationDetail(
        id=rec.id,
        morning_report_id=rec.morning_report_id,
        sector_recommendation_id=rec.sector_recommendation_id,
        ticker=rec.stock.ticker if rec.stock else "?",
        direction=rec.direction,
        priority=rec.priority,
        account=rec.account,
        reference_price=rec.reference_price,
        report_date=rec.report_date,
        logic_analysis=rec.logic_analysis,
        operation_advice=rec.operation_advice,
        created_at=rec.created_at,
        stock=StockBrief.model_validate(rec.stock) if rec.stock else None,
        executions=[ExecutionRead.model_validate(e) for e in rec.executions],
        simulations=[SimulationRead.model_validate(s) for s in rec.simulations],
    )


# ── Execute / Skip ──

@router.post("/recommendations/{rec_id}/execute", response_model=ExecutionRead,
             status_code=status.HTTP_201_CREATED)
async def execute_recommendation(
    rec_id: str,
    body: ExecutionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _get_rec_or_404(db, rec_id)
    ex = Execution(
        recommendation_id=rec_id,
        status=body.status,
        actual_price=body.actual_price,
        actual_shares=body.actual_shares,
        execution_date=body.execution_date or Date.today(),
    )
    db.add(ex)
    await db.commit()
    await db.refresh(ex)
    return ExecutionRead.model_validate(ex)


@router.post("/recommendations/{rec_id}/skip", response_model=ExecutionRead,
             status_code=status.HTTP_201_CREATED)
async def skip_recommendation(
    rec_id: str,
    body: SkipCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _get_rec_or_404(db, rec_id)
    ex = Execution(
        recommendation_id=rec_id,
        status="skipped",
        skip_reason=body.skip_reason,
        skip_note=body.skip_note,
        execution_date=Date.today(),
    )
    db.add(ex)
    await db.commit()
    await db.refresh(ex)
    return ExecutionRead.model_validate(ex)


# ── Simulations (what-if replay) ──

@router.post("/simulations", response_model=SimulationRead,
             status_code=status.HTTP_201_CREATED)
async def create_simulation(
    body: SimulationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Compute theoretical pnl for a what-if buy scenario.
    If sim_exit_price is omitted, the simulation is left open
    (sim_pnl fields stay NULL until exit is set).
    """
    rec = await _get_rec_or_404(db, body.recommendation_id)

    sim_pnl_usd: Optional[float] = None
    sim_pnl_pct: Optional[float] = None
    if body.sim_exit_price is not None:
        sim_pnl_usd = (body.sim_exit_price - body.sim_entry_price) * body.sim_entry_shares
        sim_pnl_pct = (body.sim_exit_price - body.sim_entry_price) / body.sim_entry_price * 100

    # Pull actual_pnl from a matching Execution (if any) for regret calc
    actual_pnl_usd: Optional[float] = None
    regret_usd: Optional[float] = None
    if rec.executions:
        ex = rec.executions[0]
        if (ex.status in ("executed", "partial") and ex.actual_price is not None
                and ex.actual_shares is not None and body.sim_exit_price is not None):
            actual_pnl_usd = (body.sim_exit_price - ex.actual_price) * ex.actual_shares
        elif ex.status == "skipped" and sim_pnl_usd is not None:
            actual_pnl_usd = 0.0
        if actual_pnl_usd is not None and sim_pnl_usd is not None:
            regret_usd = sim_pnl_usd - actual_pnl_usd

    sim = Simulation(
        recommendation_id=body.recommendation_id,
        sim_entry_price=body.sim_entry_price,
        sim_entry_date=body.sim_entry_date,
        sim_entry_shares=body.sim_entry_shares,
        sim_exit_price=body.sim_exit_price,
        sim_exit_date=body.sim_exit_date,
        sim_pnl_usd=sim_pnl_usd,
        sim_pnl_pct=sim_pnl_pct,
        actual_pnl_usd=actual_pnl_usd,
        regret_usd=regret_usd,
    )
    db.add(sim)
    await db.commit()
    await db.refresh(sim)
    return SimulationRead.model_validate(sim)


# ── Aggregates ──

@router.get("/review/stats", response_model=ReviewStats)
async def review_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: Optional[Date] = Query(None, alias="from"),
    to_date: Optional[Date] = Query(None, alias="to"),
):
    q = select(StockCard).options(selectinload(StockCard.executions),
                                  selectinload(StockCard.simulations))
    if from_date:
        q = q.where(StockCard.report_date >= from_date)
    if to_date:
        q = q.where(StockCard.report_date <= to_date)
    recs = (await db.execute(q)).scalars().all()

    total = len(recs)
    executed = skipped = pending = 0
    pnl_pcts: list[float] = []
    regrets: list[float] = []
    for r in recs:
        if not r.executions:
            pending += 1
        else:
            st = r.executions[0].status
            if st in ("executed", "partial"):
                executed += 1
            elif st == "skipped":
                skipped += 1
            else:
                pending += 1
        for s in r.simulations:
            if s.sim_pnl_pct is not None:
                pnl_pcts.append(s.sim_pnl_pct)
            if s.regret_usd is not None:
                regrets.append(s.regret_usd)

    rate = (executed / total * 100) if total else None
    avg_pnl = (sum(pnl_pcts) / len(pnl_pcts)) if pnl_pcts else None
    avg_regret = (sum(regrets) / len(regrets)) if regrets else None
    return ReviewStats(
        total=total, executed=executed, skipped=skipped, pending=pending,
        execution_rate_pct=round(rate, 2) if rate is not None else None,
        avg_sim_pnl_pct=round(avg_pnl, 2) if avg_pnl is not None else None,
        avg_regret_usd=round(avg_regret, 2) if avg_regret is not None else None,
    )


@router.get("/review/regrets", response_model=list[RegretItem])
async def review_regrets(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
):
    """List skipped recommendations whose simulated outcome shows a regret,
    sorted by absolute regret amount descending.
    """
    q = (
        select(Simulation, StockCard, Execution)
        .join(StockCard, Simulation.recommendation_id == StockCard.id)
        .outerjoin(Execution, Execution.recommendation_id == StockCard.id)
        .options(selectinload(StockCard.stock))
        .where(Simulation.regret_usd.is_not(None))
        .order_by(func.abs(Simulation.regret_usd).desc())
        .limit(limit)
    )
    rows = (await db.execute(q)).all()
    items = []
    for sim, rec, ex in rows:
        items.append(RegretItem(
            recommendation_id=rec.id,
            ticker=rec.stock.ticker if rec.stock else "?",
            report_date=rec.report_date,
            skip_reason=ex.skip_reason if ex else None,
            sim_pnl_usd=sim.sim_pnl_usd,
            sim_pnl_pct=sim.sim_pnl_pct,
            regret_usd=sim.regret_usd,
        ))
    return items


# ── Helpers ──

async def _get_rec_or_404(db: AsyncSession, rec_id: str) -> StockCard:
    rec = (await db.execute(
        select(StockCard).options(
            selectinload(StockCard.stock),
            selectinload(StockCard.executions),
            selectinload(StockCard.simulations),
        ).where(StockCard.id == rec_id)
    )).scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Recommendation not found")
    return rec
