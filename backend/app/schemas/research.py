from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class CitationCreate(BaseModel):
    author_org: str = Field(min_length=1, max_length=256)
    publication_date: Optional[date] = None
    source_title: str = Field(min_length=1, max_length=512)
    url: Optional[str] = None
    quality_rating: str = Field(min_length=1, max_length=2)
    claim_text: Optional[str] = None


class CitationResponse(BaseModel):
    id: str
    research_report_id: str
    author_org: str
    publication_date: Optional[date] = None
    source_title: str
    url: Optional[str] = None
    quality_rating: str
    claim_text: Optional[str] = None

    model_config = {"from_attributes": True}


class ReportCreate(BaseModel):
    stock_id: str
    phase: str = Field(min_length=1, max_length=16)
    title: str = Field(min_length=1, max_length=512)
    content: str
    signal_rating: Optional[str] = None
    confidence: Optional[str] = None
    intensity: Optional[int] = Field(default=None, ge=1, le=10)
    core_thesis: Optional[str] = None


class ReportUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    signal_rating: Optional[str] = None
    confidence: Optional[str] = None
    intensity: Optional[int] = Field(default=None, ge=1, le=10)
    core_thesis: Optional[str] = None


class ReportResponse(BaseModel):
    id: str
    stock_id: str
    phase: str
    title: str
    content: str
    signal_rating: Optional[str] = None
    confidence: Optional[str] = None
    intensity: Optional[int] = None
    core_thesis: Optional[str] = None
    stock: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
