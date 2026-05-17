from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    stock_id: str
    avg_cost: float = Field(ge=0)
    position_percent: float = Field(ge=0, le=100)
    shares: Optional[float] = Field(default=None, ge=0)
    entry_date: Optional[date] = None
    notes: Optional[str] = None


class HoldingUpdate(BaseModel):
    avg_cost: Optional[float] = Field(default=None, ge=0)
    position_percent: Optional[float] = Field(default=None, ge=0, le=100)
    shares: Optional[float] = Field(default=None, ge=0)
    entry_date: Optional[date] = None
    notes: Optional[str] = None


class StockBrief(BaseModel):
    id: str
    ticker: str
    name: str
    market: str
    sector: Optional[str] = None

    model_config = {"from_attributes": True}


class HoldingResponse(BaseModel):
    id: str
    portfolio_id: str
    stock_id: str
    ticker: str
    avg_cost: Optional[float] = None
    position_percent: Optional[float] = None
    # Snapshot dimension (populated for rows ingested via snapshot_writer)
    snapshot_id: Optional[str] = None
    snapshot_date: Optional[date] = None
    account: Optional[str] = None
    shares: Optional[float] = None
    current_price: Optional[float] = None
    market_value_usd: Optional[float] = None
    pnl_total_pct: Optional[float] = None
    pnl_day_pct: Optional[float] = None
    verdict: Optional[str] = None
    # Misc
    entry_date: Optional[date] = None
    notes: Optional[str] = None
    stock: Optional[StockBrief] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: Optional[str] = None


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PortfolioResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    holding_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PortfolioDetailResponse(PortfolioResponse):
    holdings: list[HoldingResponse] = []
