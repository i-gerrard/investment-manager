from datetime import date, datetime
from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    stock_id: str
    cost_basis: float = Field(ge=0)
    position_percent: float = Field(ge=0, le=100)
    entry_date: date | None = None
    notes: str | None = None


class HoldingUpdate(BaseModel):
    cost_basis: float | None = Field(default=None, ge=0)
    position_percent: float | None = Field(default=None, ge=0, le=100)
    entry_date: date | None = None
    notes: str | None = None


class HoldingResponse(BaseModel):
    id: str
    portfolio_id: str
    stock_id: str
    ticker: str
    cost_basis: float
    position_percent: float
    entry_date: date | None = None
    notes: str | None = None
    stock: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None


class PortfolioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class PortfolioResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    holding_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class PortfolioDetailResponse(PortfolioResponse):
    holdings: list[HoldingResponse] = []
