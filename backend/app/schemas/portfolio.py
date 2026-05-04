from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    stock_id: str
    cost_basis: float = Field(ge=0)
    position_percent: float = Field(ge=0, le=100)
    entry_date: Optional[date] = None
    notes: Optional[str] = None


class HoldingUpdate(BaseModel):
    cost_basis: Optional[float] = Field(default=None, ge=0)
    position_percent: Optional[float] = Field(default=None, ge=0, le=100)
    entry_date: Optional[date] = None
    notes: Optional[str] = None


class HoldingResponse(BaseModel):
    id: str
    portfolio_id: str
    stock_id: str
    ticker: str
    cost_basis: float
    position_percent: float
    entry_date: Optional[date] = None
    notes: Optional[str] = None
    stock: Optional[dict] = None
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
