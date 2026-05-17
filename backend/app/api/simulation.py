from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.portfolio import Holding, Portfolio
from app.models.simulation import (
    SimulatedPortfolio,
    SimulatedPosition,
    SimulatedTrade,
    TradeReview,
)
from app.models.stock import Stock
from app.models.user import User
from app.schemas.simulation import (
    HoldingSnapshot,
    PortfolioComparison,
    SimulatedPortfolioCreate,
    SimulatedPortfolioResponse,
    SimulatedPositionResponse,
    SimulatedTradeResponse,
    TradeExecuteRequest,
    TradeReviewCreate,
    TradeReviewResponse,
)
from app.services import market_data
from app.services.simulation_engine import (
    calc_equity,
    calc_margin_level,
    calc_unrealized_pnl,
    execute_trade,
    is_margin_call,
)

router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_portfolio(
    portfolio_id: str, user: User, db: AsyncSession
) -> SimulatedPortfolio:
    result = await db.execute(
        select(SimulatedPortfolio).where(
            SimulatedPortfolio.id == portfolio_id,
            SimulatedPortfolio.user_id == user.id,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(404, "Simulated portfolio not found")
    return portfolio


async def _open_positions(portfolio_id: str, db: AsyncSession) -> list[SimulatedPosition]:
    result = await db.execute(
        select(SimulatedPosition).where(SimulatedPosition.portfolio_id == portfolio_id)
    )
    return list(result.scalars().all())


def _enrich_portfolio(
    portfolio: SimulatedPortfolio,
    positions: list[SimulatedPosition],
    prices: dict[str, float],
) -> SimulatedPortfolioResponse:
    total_margin = sum(p.margin_used for p in positions)
    unrealized = sum(
        calc_unrealized_pnl(p, prices.get(p.ticker, p.avg_entry_price)) for p in positions
    )
    equity = portfolio.cash_balance + total_margin + unrealized
    margin_level = calc_margin_level(equity, total_margin)
    margin_call_flag = is_margin_call(equity, total_margin, portfolio.maintenance_margin_rate)
    return_pct = (equity - portfolio.initial_capital) / portfolio.initial_capital * 100

    return SimulatedPortfolioResponse(
        id=portfolio.id,
        user_id=portfolio.user_id,
        name=portfolio.name,
        initial_capital=portfolio.initial_capital,
        cash_balance=portfolio.cash_balance,
        currency=portfolio.currency,
        max_leverage=portfolio.max_leverage,
        maintenance_margin_rate=portfolio.maintenance_margin_rate,
        is_active=portfolio.is_active,
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
        total_margin_used=total_margin,
        unrealized_pnl=unrealized,
        equity=equity,
        margin_level=margin_level,
        margin_call=margin_call_flag,
        total_return_pct=return_pct,
    )


def _enrich_position(pos: SimulatedPosition, prices: dict[str, float]) -> SimulatedPositionResponse:
    current = prices.get(pos.ticker)
    unrealized = calc_unrealized_pnl(pos, current) if current else None
    pnl_pct = (unrealized / pos.margin_used * 100) if (unrealized is not None and pos.margin_used) else None
    return SimulatedPositionResponse(
        id=pos.id,
        portfolio_id=pos.portfolio_id,
        ticker=pos.ticker,
        direction=pos.direction,
        quantity=pos.quantity,
        avg_entry_price=pos.avg_entry_price,
        leverage_ratio=pos.leverage_ratio,
        margin_used=pos.margin_used,
        notional_value=pos.notional_value,
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        opened_at=pos.opened_at,
        current_price=current,
        unrealized_pnl=unrealized,
        unrealized_pnl_pct=pnl_pct,
    )


# ── Portfolio endpoints ───────────────────────────────────────────────────────

@router.post("/portfolios", response_model=SimulatedPortfolioResponse, status_code=201)
async def create_portfolio(
    body: SimulatedPortfolioCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = SimulatedPortfolio(
        user_id=user.id,
        name=body.name,
        initial_capital=body.initial_capital,
        cash_balance=body.initial_capital,
        currency=body.currency,
        max_leverage=body.max_leverage,
        maintenance_margin_rate=body.maintenance_margin_rate,
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return _enrich_portfolio(portfolio, [], {})


@router.get("/portfolios", response_model=list[SimulatedPortfolioResponse])
async def list_portfolios(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SimulatedPortfolio).where(SimulatedPortfolio.user_id == user.id)
    )
    portfolios = list(result.scalars().all())
    out = []
    for p in portfolios:
        positions = await _open_positions(p.id, db)
        tickers = list({pos.ticker for pos in positions})
        prices = await market_data.get_prices(tickers) if tickers else {}
        out.append(_enrich_portfolio(p, positions, prices))
    return out


@router.get("/portfolios/{portfolio_id}", response_model=SimulatedPortfolioResponse)
async def get_portfolio(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await _get_portfolio(portfolio_id, user, db)
    positions = await _open_positions(portfolio_id, db)
    tickers = list({p.ticker for p in positions})
    prices = await market_data.get_prices(tickers) if tickers else {}
    return _enrich_portfolio(portfolio, positions, prices)


# ── Price lookup ──────────────────────────────────────────────────────────────

@router.get("/price/{ticker}")
async def get_price(
    ticker: str,
    _: User = Depends(get_current_user),
):
    try:
        price = await market_data.get_price(ticker.upper())
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ticker": ticker.upper(), "price": price}


# ── Trade execution ───────────────────────────────────────────────────────────

@router.post("/portfolios/{portfolio_id}/trades", response_model=SimulatedTradeResponse, status_code=201)
async def execute_trade_endpoint(
    portfolio_id: str,
    body: TradeExecuteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    portfolio = await _get_portfolio(portfolio_id, user, db)

    if body.use_market_price:
        try:
            price = await market_data.get_price(body.ticker.upper())
        except ValueError as e:
            raise HTTPException(422, str(e))
    else:
        if body.custom_price is None:
            raise HTTPException(422, "custom_price required when use_market_price=false")
        price = body.custom_price

    positions = await _open_positions(portfolio_id, db)

    # Resolve stock_id from ticker if it exists in the stocks table
    stock_result = await db.execute(select(Stock).where(Stock.ticker == body.ticker.upper()))
    stock = stock_result.scalar_one_or_none()

    trade, position_out, _ = execute_trade(
        portfolio,
        positions,
        ticker=body.ticker.upper(),
        action=body.action,
        quantity=body.quantity,
        price=price,
        leverage_ratio=body.leverage_ratio,
        rationale=body.rationale,
        triggered_by=body.triggered_by,
        signal_id=body.signal_id,
        stop_loss=body.stop_loss,
        take_profit=body.take_profit,
        stock_id=stock.id if stock else None,
    )

    # Persist: remove closed position
    if position_out is None:
        await db.execute(
            delete(SimulatedPosition).where(
                SimulatedPosition.portfolio_id == portfolio_id,
                SimulatedPosition.ticker == body.ticker.upper(),
                SimulatedPosition.direction == ("LONG" if body.action == "SELL_LONG" else "SHORT"),
            )
        )
    elif position_out.id:
        db.add(position_out)
    else:
        db.add(position_out)

    db.add(trade)
    db.add(portfolio)
    await db.commit()
    await db.refresh(trade)
    return SimulatedTradeResponse.model_validate(trade)


# ── Positions ─────────────────────────────────────────────────────────────────

@router.get("/portfolios/{portfolio_id}/positions", response_model=list[SimulatedPositionResponse])
async def list_positions(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_portfolio(portfolio_id, user, db)
    positions = await _open_positions(portfolio_id, db)
    tickers = list({p.ticker for p in positions})
    prices = await market_data.get_prices(tickers) if tickers else {}
    return [_enrich_position(p, prices) for p in positions]


# ── Trade history ─────────────────────────────────────────────────────────────

@router.get("/portfolios/{portfolio_id}/trades", response_model=list[SimulatedTradeResponse])
async def list_trades(
    portfolio_id: str,
    ticker: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_portfolio(portfolio_id, user, db)

    stmt = (
        select(SimulatedTrade)
        .where(SimulatedTrade.portfolio_id == portfolio_id)
        .order_by(SimulatedTrade.executed_at.desc())
        .limit(limit)
    )
    if ticker:
        stmt = stmt.where(SimulatedTrade.ticker == ticker.upper())
    if action:
        stmt = stmt.where(SimulatedTrade.action == action)

    result = await db.execute(stmt)
    return [SimulatedTradeResponse.model_validate(t) for t in result.scalars().all()]


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.post("/portfolios/{portfolio_id}/reviews", response_model=TradeReviewResponse, status_code=201)
async def create_review(
    portfolio_id: str,
    body: TradeReviewCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_portfolio(portfolio_id, user, db)

    if body.trade_id:
        trade_result = await db.execute(
            select(SimulatedTrade).where(
                SimulatedTrade.id == body.trade_id,
                SimulatedTrade.portfolio_id == portfolio_id,
            )
        )
        if not trade_result.scalar_one_or_none():
            raise HTTPException(404, "Trade not found in this portfolio")

    review = TradeReview(
        portfolio_id=portfolio_id,
        trade_id=body.trade_id,
        ticker=body.ticker.upper(),
        entry_rationale=body.entry_rationale,
        actual_outcome=body.actual_outcome,
        pnl_realized=body.pnl_realized,
        lessons_learned=body.lessons_learned,
        rating=body.rating,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return TradeReviewResponse.model_validate(review)


@router.get("/portfolios/{portfolio_id}/reviews", response_model=list[TradeReviewResponse])
async def list_reviews(
    portfolio_id: str,
    ticker: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_portfolio(portfolio_id, user, db)

    stmt = (
        select(TradeReview)
        .where(TradeReview.portfolio_id == portfolio_id)
        .order_by(TradeReview.reviewed_at.desc())
    )
    if ticker:
        stmt = stmt.where(TradeReview.ticker == ticker.upper())

    result = await db.execute(stmt)
    return [TradeReviewResponse.model_validate(r) for r in result.scalars().all()]


# ── Sim vs Real comparison ────────────────────────────────────────────────────

@router.get("/portfolios/{portfolio_id}/comparison", response_model=PortfolioComparison)
async def compare_with_real(
    portfolio_id: str,
    real_portfolio_id: Optional[str] = Query(None, description="Real portfolio ID to compare against"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sim = await _get_portfolio(portfolio_id, user, db)
    sim_positions = await _open_positions(portfolio_id, db)

    # Collect all tickers we need prices for
    sim_tickers = {p.ticker for p in sim_positions}

    # Fetch real portfolio if requested
    real_portfolio = None
    real_holdings: list[Holding] = []

    if real_portfolio_id:
        rp_result = await db.execute(
            select(Portfolio).where(
                Portfolio.id == real_portfolio_id,
                Portfolio.user_id == user.id,
            )
        )
        real_portfolio = rp_result.scalar_one_or_none()
        if not real_portfolio:
            raise HTTPException(404, "Real portfolio not found")

        holdings_result = await db.execute(
            select(Holding).where(Holding.portfolio_id == real_portfolio_id)
        )
        real_holdings = list(holdings_result.scalars().all())

    real_tickers = {h.ticker for h in real_holdings}
    all_tickers = list(sim_tickers | real_tickers)
    prices = await market_data.get_prices(all_tickers) if all_tickers else {}

    # Sim metrics
    total_margin = sum(p.margin_used for p in sim_positions)
    sim_unrealized = sum(
        calc_unrealized_pnl(p, prices.get(p.ticker, p.avg_entry_price)) for p in sim_positions
    )
    sim_equity = sim.cash_balance + total_margin + sim_unrealized
    sim_return_pct = (sim_equity - sim.initial_capital) / sim.initial_capital * 100

    enriched_positions = [_enrich_position(p, prices) for p in sim_positions]

    # Real portfolio metrics
    holding_snapshots: list[HoldingSnapshot] = []
    real_return_pct: Optional[float] = None

    if real_holdings:
        # Skip rows missing avg_cost/position_percent (manual holdings or
        # partial snapshot ingests can have these as NULL).
        priced_holdings = [
            h for h in real_holdings if h.avg_cost is not None and h.position_percent is not None
        ]
        total_cost = sum(h.avg_cost * (h.position_percent / 100) for h in priced_holdings)
        total_current = 0.0
        for h in priced_holdings:
            current = prices.get(h.ticker)
            weight = h.position_percent / 100
            cost = h.avg_cost * weight
            unrealized = (current - h.avg_cost) * weight if current else None
            pnl_pct = ((current - h.avg_cost) / h.avg_cost * 100) if current else None
            total_current += (current * weight) if current else cost
            holding_snapshots.append(
                HoldingSnapshot(
                    ticker=h.ticker,
                    cost_basis=h.avg_cost,
                    current_price=current,
                    position_percent=h.position_percent,
                    unrealized_pnl=unrealized,
                    unrealized_pnl_pct=pnl_pct,
                )
            )
        if total_cost > 0:
            real_return_pct = (total_current - total_cost) / total_cost * 100

    alpha_pct: Optional[float] = None
    if real_return_pct is not None:
        alpha_pct = sim_return_pct - real_return_pct

    return PortfolioComparison(
        comparison_date=datetime.utcnow(),
        sim_name=sim.name,
        sim_equity=sim_equity,
        sim_initial_capital=sim.initial_capital,
        sim_return_pct=sim_return_pct,
        sim_unrealized_pnl=sim_unrealized,
        sim_positions=enriched_positions,
        real_portfolio_name=real_portfolio.name if real_portfolio else None,
        real_holdings=holding_snapshots,
        real_return_pct=real_return_pct,
        alpha_pct=alpha_pct,
    )
