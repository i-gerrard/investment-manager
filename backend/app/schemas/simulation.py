from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Portfolio ─────────────────────────────────────────────────────────────────

class SimulatedPortfolioCreate(BaseModel):
    name: str = Field(..., max_length=128)
    initial_capital: float = Field(..., gt=0)
    currency: str = Field("USD", max_length=8)
    max_leverage: float = Field(10.0, gt=0)
    maintenance_margin_rate: float = Field(0.5, gt=0, le=1)


class SimulatedPortfolioResponse(BaseModel):
    id: str
    user_id: str
    name: str
    initial_capital: float
    cash_balance: float
    currency: str
    max_leverage: float
    maintenance_margin_rate: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    # Runtime-computed from live prices
    total_margin_used: float = 0.0
    unrealized_pnl: float = 0.0
    equity: float = 0.0
    margin_level: Optional[float] = None  # None when no open positions
    margin_call: bool = False
    total_return_pct: float = 0.0

    model_config = {"from_attributes": True}


# ── Position ──────────────────────────────────────────────────────────────────

class SimulatedPositionResponse(BaseModel):
    id: str
    portfolio_id: str
    ticker: str
    direction: str
    quantity: float
    avg_entry_price: float
    leverage_ratio: float
    margin_used: float
    notional_value: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    opened_at: datetime
    # Runtime-computed
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None

    model_config = {"from_attributes": True}


# ── Trade ─────────────────────────────────────────────────────────────────────

class TradeExecuteRequest(BaseModel):
    ticker: str = Field(..., max_length=16)
    # BUY_LONG | SELL_LONG | SELL_SHORT | BUY_SHORT
    action: str
    quantity: float = Field(..., gt=0)
    leverage_ratio: float = Field(1.0, ge=1.0)
    rationale: str = Field(..., min_length=10)
    triggered_by: str = Field("MANUAL")
    signal_id: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    # If False, supply custom_price instead of fetching live price
    use_market_price: bool = True
    custom_price: Optional[float] = Field(None, gt=0)


class SimulatedTradeResponse(BaseModel):
    id: str
    portfolio_id: str
    ticker: str
    action: str
    quantity: float
    price: float
    leverage_ratio: float
    margin_used: float
    notional_value: float
    rationale: str
    triggered_by: str
    signal_id: Optional[str]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    realized_pnl: Optional[float]
    fees: float
    executed_at: datetime

    model_config = {"from_attributes": True}


# ── Trade Review ──────────────────────────────────────────────────────────────

class TradeReviewCreate(BaseModel):
    trade_id: Optional[str] = None
    ticker: str = Field(..., max_length=16)
    entry_rationale: str
    actual_outcome: str
    pnl_realized: float = 0.0
    lessons_learned: Optional[str] = None
    rating: int = Field(3, ge=1, le=5)


class TradeReviewResponse(BaseModel):
    id: str
    portfolio_id: str
    trade_id: Optional[str]
    ticker: str
    entry_rationale: str
    actual_outcome: str
    pnl_realized: float
    lessons_learned: Optional[str]
    rating: int
    reviewed_at: datetime

    model_config = {"from_attributes": True}


# ── Comparison (sim vs real) ──────────────────────────────────────────────────

class HoldingSnapshot(BaseModel):
    ticker: str
    cost_basis: float
    current_price: Optional[float]
    position_percent: float
    unrealized_pnl: Optional[float]
    unrealized_pnl_pct: Optional[float]


class PortfolioComparison(BaseModel):
    comparison_date: datetime
    sim_name: str
    sim_equity: float
    sim_initial_capital: float
    sim_return_pct: float
    sim_unrealized_pnl: float
    sim_positions: list[SimulatedPositionResponse]
    real_portfolio_name: Optional[str]
    real_holdings: list[HoldingSnapshot]
    real_return_pct: Optional[float]
    # sim total return minus real portfolio return
    alpha_pct: Optional[float]
