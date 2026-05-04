"""
CFD simulation engine.

Margin model:
  margin_used    = notional_value / leverage_ratio
  notional_value = quantity * price

P&L:
  LONG  unrealized = (current_price - avg_entry_price) * quantity
  SHORT unrealized = (avg_entry_price - current_price) * quantity

Equity:
  equity = cash_balance + total_margin_used + total_unrealized_pnl

Margin level:
  margin_level = equity / total_margin_used
  margin call   when margin_level < portfolio.maintenance_margin_rate
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from app.models.simulation import SimulatedPortfolio, SimulatedPosition, SimulatedTrade

if TYPE_CHECKING:
    pass

VALID_ACTIONS = {"BUY_LONG", "SELL_LONG", "SELL_SHORT", "BUY_SHORT"}


# ── Core maths ────────────────────────────────────────────────────────────────

def calc_unrealized_pnl(position: SimulatedPosition, current_price: float) -> float:
    if position.direction == "LONG":
        return (current_price - position.avg_entry_price) * position.quantity
    return (position.avg_entry_price - current_price) * position.quantity


def calc_equity(
    cash_balance: float,
    positions: list[SimulatedPosition],
    prices: dict[str, float],
) -> float:
    total_pnl = sum(
        calc_unrealized_pnl(p, prices.get(p.ticker, p.avg_entry_price))
        for p in positions
    )
    total_margin = sum(p.margin_used for p in positions)
    return cash_balance + total_margin + total_pnl


def calc_margin_level(equity: float, total_margin: float) -> float | None:
    if total_margin == 0:
        return None
    return equity / total_margin


def is_margin_call(equity: float, total_margin: float, maintenance_rate: float) -> bool:
    level = calc_margin_level(equity, total_margin)
    return level is not None and level < maintenance_rate


# ── Trade validation ──────────────────────────────────────────────────────────

def validate_action(action: str) -> None:
    if action not in VALID_ACTIONS:
        raise HTTPException(400, f"Invalid action '{action}'. Must be one of {VALID_ACTIONS}")


def validate_leverage(leverage_ratio: float, max_leverage: float) -> None:
    if leverage_ratio > max_leverage:
        raise HTTPException(
            400,
            f"Requested leverage {leverage_ratio}x exceeds portfolio max {max_leverage}x",
        )


def validate_sufficient_cash(cash_balance: float, margin_required: float) -> None:
    if cash_balance < margin_required:
        raise HTTPException(
            400,
            f"Insufficient cash. Need {margin_required:.2f}, have {cash_balance:.2f}",
        )


# ── Position helpers ──────────────────────────────────────────────────────────

def find_position(
    positions: list[SimulatedPosition], ticker: str, direction: str
) -> SimulatedPosition | None:
    return next(
        (p for p in positions if p.ticker == ticker and p.direction == direction), None
    )


def required_direction(action: str) -> str:
    return "LONG" if action in ("BUY_LONG", "SELL_LONG") else "SHORT"


def is_opening(action: str) -> bool:
    return action in ("BUY_LONG", "SELL_SHORT")


# ── Trade execution ───────────────────────────────────────────────────────────

def execute_trade(
    portfolio: SimulatedPortfolio,
    positions: list[SimulatedPosition],
    *,
    ticker: str,
    action: str,
    quantity: float,
    price: float,
    leverage_ratio: float,
    rationale: str,
    triggered_by: str,
    signal_id: str | None,
    stop_loss: float | None,
    take_profit: float | None,
    stock_id: str | None,
) -> tuple[SimulatedTrade, SimulatedPosition | None, float]:
    """
    Apply a CFD trade to the portfolio.

    Returns:
        trade          — the new SimulatedTrade record (not yet persisted)
        position       — the updated/new SimulatedPosition (None if fully closed)
        realized_pnl   — non-zero only when closing a position
    """
    validate_action(action)
    validate_leverage(leverage_ratio, portfolio.max_leverage)

    notional = quantity * price
    margin = notional / leverage_ratio
    direction = required_direction(action)
    opening = is_opening(action)
    realized_pnl = 0.0

    existing = find_position(positions, ticker, direction)

    if opening:
        validate_sufficient_cash(portfolio.cash_balance, margin)
        portfolio.cash_balance -= margin

        if existing:
            # Average in to existing position
            total_qty = existing.quantity + quantity
            existing.avg_entry_price = (
                existing.avg_entry_price * existing.quantity + price * quantity
            ) / total_qty
            existing.quantity = total_qty
            existing.notional_value = total_qty * existing.avg_entry_price
            existing.margin_used += margin
            if stop_loss is not None:
                existing.stop_loss = stop_loss
            if take_profit is not None:
                existing.take_profit = take_profit
            position_out = existing
        else:
            position_out = SimulatedPosition(
                portfolio_id=portfolio.id,
                stock_id=stock_id,
                ticker=ticker,
                direction=direction,
                quantity=quantity,
                avg_entry_price=price,
                leverage_ratio=leverage_ratio,
                margin_used=margin,
                notional_value=notional,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

    else:
        # Closing trade
        if existing is None or existing.quantity < quantity:
            available = existing.quantity if existing else 0
            raise HTTPException(
                400,
                f"Cannot close {quantity} {ticker} {direction}: only {available} open",
            )

        realized_pnl = calc_unrealized_pnl(
            SimulatedPosition(
                portfolio_id=portfolio.id,
                ticker=ticker,
                direction=direction,
                quantity=quantity,
                avg_entry_price=existing.avg_entry_price,
                leverage_ratio=leverage_ratio,
                margin_used=margin,
                notional_value=notional,
            ),
            price,
        )

        close_margin = (quantity / existing.quantity) * existing.margin_used
        portfolio.cash_balance += close_margin + realized_pnl

        remaining = existing.quantity - quantity
        if remaining <= 1e-9:
            position_out = None  # fully closed — caller must delete the DB row
            existing.quantity = 0
        else:
            existing.quantity = remaining
            existing.margin_used = (remaining / (remaining + quantity)) * existing.margin_used
            existing.notional_value = remaining * existing.avg_entry_price
            position_out = existing

    trade = SimulatedTrade(
        portfolio_id=portfolio.id,
        stock_id=stock_id,
        ticker=ticker,
        action=action,
        quantity=quantity,
        price=price,
        leverage_ratio=leverage_ratio,
        margin_used=margin,
        notional_value=notional,
        rationale=rationale,
        triggered_by=triggered_by,
        signal_id=signal_id,
        stop_loss=stop_loss,
        take_profit=take_profit,
        realized_pnl=realized_pnl if not opening else None,
        fees=0.0,
    )

    return trade, position_out, realized_pnl
