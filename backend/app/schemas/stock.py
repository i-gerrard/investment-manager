from datetime import datetime
from pydantic import BaseModel, Field


class StockCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=256)
    market: str = Field(min_length=1, max_length=16)
    sector: str | None = None
    industry: str | None = None


class StockUpdate(BaseModel):
    ticker: str | None = None
    name: str | None = None
    market: str | None = None
    sector: str | None = None
    industry: str | None = None


class StockResponse(BaseModel):
    id: str
    ticker: str
    name: str
    market: str
    sector: str | None = None
    industry: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StockListResponse(BaseModel):
    items: list[StockResponse]
    total: int
