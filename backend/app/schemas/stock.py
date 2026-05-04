from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StockCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=256)
    market: str = Field(min_length=1, max_length=16)
    sector: Optional[str] = None
    industry: Optional[str] = None


class StockUpdate(BaseModel):
    ticker: Optional[str] = None
    name: Optional[str] = None
    market: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


class StockResponse(BaseModel):
    id: str
    ticker: str
    name: str
    market: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StockListResponse(BaseModel):
    items: list[StockResponse]
    total: int
