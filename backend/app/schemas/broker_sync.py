from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BrokerPosition(BaseModel):
    """A single position as captured from the broker's website."""
    ticker: str
    name: str
    quantity: float
    current_price: float
    avg_cost: Optional[float] = None
    market_value: float
    pnl_pct: Optional[float] = None
    currency: str = "USD"


class BrokerIngestRequest(BaseModel):
    """Payload the sync script POSTs after reading a broker's positions."""
    broker: str = Field(..., pattern="^(etoro|tr)$")
    positions: list[BrokerPosition]
    # If provided, sync into this portfolio; otherwise use the saved mapping
    portfolio_id: Optional[str] = None


class BrokerSyncLogResponse(BaseModel):
    id: str
    broker: str
    status: str
    positions_read: int
    positions_synced: int
    portfolio_id: Optional[str]
    error_msg: Optional[str]
    started_at: datetime
    finished_at: Optional[datetime]

    model_config = {"from_attributes": True}


class BrokerPortfolioMappingCreate(BaseModel):
    broker: str = Field(..., pattern="^(etoro|tr)$")
    portfolio_id: str


class BrokerPortfolioMappingResponse(BaseModel):
    id: str
    broker: str
    portfolio_id: str
    portfolio_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BrokerSyncStatusResponse(BaseModel):
    """Aggregated status for the sync dashboard."""
    etoro_last_sync: Optional[BrokerSyncLogResponse]
    tr_last_sync: Optional[BrokerSyncLogResponse]
    etoro_mapping: Optional[BrokerPortfolioMappingResponse]
    tr_mapping: Optional[BrokerPortfolioMappingResponse]
