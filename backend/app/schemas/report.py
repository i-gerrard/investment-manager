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
