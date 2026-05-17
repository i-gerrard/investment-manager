from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class SnapshotListItem(BaseModel):
    id: str
    report_date: date
    source: str
    combined_total_usd: Optional[float] = None
    combined_cash_usd: Optional[float] = None
    cash_ratio_pct: Optional[float] = None
    holdings_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class SnapshotDetail(BaseModel):
    id: str
    user_id: str
    report_date: date
    source: str
    # eToro
    etoro_total_usd: Optional[float] = None
    etoro_cash_usd: Optional[float] = None
    etoro_invested_usd: Optional[float] = None
    etoro_pnl_day_usd: Optional[float] = None
    # TR
    tr_total_eur: Optional[float] = None
    tr_cash_eur: Optional[float] = None
    tr_invested_eur: Optional[float] = None
    tr_pnl_day_eur: Optional[float] = None
    # Combined
    eur_usd_rate: Optional[float] = None
    combined_total_usd: Optional[float] = None
    combined_cash_usd: Optional[float] = None
    cash_ratio_pct: Optional[float] = None
    holdings_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class HoldingSnapshotRow(BaseModel):
    id: str
    ticker: str
    account: Optional[str] = None
    shares: Optional[float] = None
    avg_cost: Optional[float] = None
    current_price: Optional[float] = None
    market_value_usd: Optional[float] = None
    pnl_total_pct: Optional[float] = None
    pnl_day_pct: Optional[float] = None
    position_percent: Optional[float] = None
    verdict: Optional[str] = None

    model_config = {"from_attributes": True}


class HoldingDiff(BaseModel):
    ticker: str
    account: Optional[str] = None
    # 'added' | 'removed' | 'changed' | 'unchanged'
    change_type: str
    from_shares: Optional[float] = None
    to_shares: Optional[float] = None
    shares_delta: Optional[float] = None
    from_market_value_usd: Optional[float] = None
    to_market_value_usd: Optional[float] = None
    value_delta_usd: Optional[float] = None
    from_pnl_pct: Optional[float] = None
    to_pnl_pct: Optional[float] = None


class SnapshotCompare(BaseModel):
    from_date: date
    to_date: date
    from_total_usd: Optional[float] = None
    to_total_usd: Optional[float] = None
    total_delta_usd: Optional[float] = None
    from_cash_usd: Optional[float] = None
    to_cash_usd: Optional[float] = None
    cash_delta_usd: Optional[float] = None
    holdings: list[HoldingDiff] = []


class HoldingHistoryPoint(BaseModel):
    report_date: date
    account: Optional[str] = None
    shares: Optional[float] = None
    avg_cost: Optional[float] = None
    current_price: Optional[float] = None
    market_value_usd: Optional[float] = None
    pnl_total_pct: Optional[float] = None


class PortfolioSummaryPoint(BaseModel):
    report_date: date
    combined_total_usd: Optional[float] = None
    combined_cash_usd: Optional[float] = None
    cash_ratio_pct: Optional[float] = None
    etoro_total_usd: Optional[float] = None
    tr_total_eur: Optional[float] = None
