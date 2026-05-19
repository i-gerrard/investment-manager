from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class MorningReportCreate(BaseModel):
    report_date: date
    html_content: str
    headline: Optional[str] = None
    key_themes: Optional[list[str]] = None
    macro_signals: Optional[list[dict]] = None


class MorningReportResponse(BaseModel):
    id: str
    report_date: date
    html_content: str
    headline: Optional[str] = None
    key_themes: Optional[list] = None
    macro_signals: Optional[list] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MorningReportListResponse(BaseModel):
    id: str
    report_date: date
    headline: Optional[str] = None

    model_config = {"from_attributes": True}


class SynthesisReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    content: str
    thematic_clusters: Optional[list] = None
    risk_factors: Optional[list] = None
    signal_rating: Optional[str] = None
    confidence: Optional[str] = None


class SynthesisReportResponse(BaseModel):
    id: str
    title: str
    content: str
    thematic_clusters: Optional[list] = None
    risk_factors: Optional[list] = None
    signal_rating: Optional[str] = None
    confidence: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Report upload (HTML → snapshot) ──

class ReportUploadRequest(BaseModel):
    html: str = Field(min_length=100)
    report_date: Optional[date] = None  # override if HTML doesn't contain it


class ReportUploadResponse(BaseModel):
    snapshot_id: str
    morning_report_id: str
    report_date: date
    source: str
    holdings_count: int
    recommendations_parsed: int  # extracted from HTML
    recommendations_persisted: int = 0  # written as standalone StockCard rows
    skipped_holdings: int = 0  # holdings without an account mapping
    skipped_recommendations: int = 0  # rows where ticker couldn't be extracted


# ── Bulk load from a server-side directory ──

class BulkLoadRequest(BaseModel):
    path: str = Field(min_length=1)
    pattern: str = "**/report-*.html"


class BulkLoadFileResult(BaseModel):
    file: str
    report_date: Optional[date] = None
    snapshot_id: Optional[str] = None
    holdings: Optional[int] = None
    recommendations: Optional[int] = None
    error: Optional[str] = None


class BulkLoadResponse(BaseModel):
    path: str
    pattern: str
    found: int
    loaded: int
    failed: int
    files: list[BulkLoadFileResult]
