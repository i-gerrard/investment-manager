from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Recommendation read models ──

class StockBrief(BaseModel):
    id: str
    ticker: str
    name: str

    model_config = {"from_attributes": True}


class ExecutionRead(BaseModel):
    id: str
    status: str
    actual_price: Optional[float] = None
    actual_shares: Optional[float] = None
    execution_date: Optional[date] = None
    skip_reason: Optional[str] = None
    skip_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SimulationRead(BaseModel):
    id: str
    sim_entry_price: float
    sim_entry_date: date
    sim_entry_shares: float
    sim_exit_price: Optional[float] = None
    sim_exit_date: Optional[date] = None
    sim_pnl_usd: Optional[float] = None
    sim_pnl_pct: Optional[float] = None
    actual_pnl_usd: Optional[float] = None
    regret_usd: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationListItem(BaseModel):
    id: str
    ticker: str
    direction: str
    priority: Optional[str] = None
    account: Optional[str] = None
    reference_price: Optional[float] = None
    report_date: Optional[date] = None
    operation_advice: Optional[str] = None
    has_execution: bool = False
    execution_status: Optional[str] = None  # 'executed' | 'skipped' | 'partial'
    stock: Optional[StockBrief] = None


class RecommendationDetail(BaseModel):
    id: str
    morning_report_id: Optional[str] = None
    sector_recommendation_id: Optional[str] = None
    ticker: str
    direction: str
    priority: Optional[str] = None
    account: Optional[str] = None
    reference_price: Optional[float] = None
    report_date: Optional[date] = None
    logic_analysis: Optional[str] = None
    operation_advice: Optional[str] = None
    created_at: datetime
    stock: Optional[StockBrief] = None
    executions: list[ExecutionRead] = []
    simulations: list[SimulationRead] = []


# ── Execution write models ──

class ExecutionCreate(BaseModel):
    status: Literal["executed", "partial"] = "executed"
    actual_price: float = Field(ge=0)
    actual_shares: float = Field(gt=0)
    execution_date: Optional[date] = None


class SkipCreate(BaseModel):
    skip_reason: Literal["forgot", "disagreed", "no_cash", "waiting_better_price", "other"]
    skip_note: Optional[str] = None


# ── Simulation write models ──

class SimulationCreate(BaseModel):
    recommendation_id: str
    sim_entry_price: float = Field(gt=0)
    sim_entry_date: date
    sim_entry_shares: float = Field(gt=0)
    sim_exit_price: Optional[float] = Field(default=None, gt=0)
    sim_exit_date: Optional[date] = None


# ── Aggregate review stats ──

class ReviewStats(BaseModel):
    total: int
    executed: int
    skipped: int
    pending: int  # no execution recorded
    execution_rate_pct: Optional[float] = None
    avg_sim_pnl_pct: Optional[float] = None  # mean of simulations.sim_pnl_pct
    avg_regret_usd: Optional[float] = None


class RegretItem(BaseModel):
    recommendation_id: str
    ticker: str
    report_date: Optional[date] = None
    skip_reason: Optional[str] = None
    sim_pnl_usd: Optional[float] = None
    sim_pnl_pct: Optional[float] = None
    regret_usd: Optional[float] = None
