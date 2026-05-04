from datetime import date, datetime
from pydantic import BaseModel, Field


class MorningReportCreate(BaseModel):
    report_date: date
    html_content: str
    headline: str | None = None
    key_themes: list[str] | None = None
    macro_signals: list[dict] | None = None


class MorningReportResponse(BaseModel):
    id: str
    report_date: date
    html_content: str
    headline: str | None = None
    key_themes: list | None = None
    macro_signals: list | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MorningReportListResponse(BaseModel):
    id: str
    report_date: date
    headline: str | None = None

    model_config = {"from_attributes": True}


class SynthesisReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    content: str
    thematic_clusters: list | None = None
    risk_factors: list | None = None
    signal_rating: str | None = None
    confidence: str | None = None


class SynthesisReportResponse(BaseModel):
    id: str
    title: str
    content: str
    thematic_clusters: list | None = None
    risk_factors: list | None = None
    signal_rating: str | None = None
    confidence: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
