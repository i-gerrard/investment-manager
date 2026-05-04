from datetime import date, datetime
from pydantic import BaseModel, Field


class CitationCreate(BaseModel):
    author_org: str = Field(min_length=1, max_length=256)
    publication_date: date | None = None
    source_title: str = Field(min_length=1, max_length=512)
    url: str | None = None
    quality_rating: str = Field(min_length=1, max_length=2)
    claim_text: str | None = None


class CitationResponse(BaseModel):
    id: str
    research_report_id: str
    author_org: str
    publication_date: date | None = None
    source_title: str
    url: str | None = None
    quality_rating: str
    claim_text: str | None = None

    model_config = {"from_attributes": True}


class ReportCreate(BaseModel):
    stock_id: str
    phase: str = Field(min_length=1, max_length=16)
    title: str = Field(min_length=1, max_length=512)
    content: str
    signal_rating: str | None = None
    confidence: str | None = None
    intensity: int | None = Field(default=None, ge=1, le=10)
    core_thesis: str | None = None


class ReportUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    signal_rating: str | None = None
    confidence: str | None = None
    intensity: int | None = Field(default=None, ge=1, le=10)
    core_thesis: str | None = None


class ReportResponse(BaseModel):
    id: str
    stock_id: str
    phase: str
    title: str
    content: str
    signal_rating: str | None = None
    confidence: str | None = None
    intensity: int | None = None
    core_thesis: str | None = None
    stock: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
