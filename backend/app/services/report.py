from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import MorningReport, SynthesisReport
from app.schemas.report import (
    MorningReportCreate,
    MorningReportResponse,
    MorningReportListResponse,
    SynthesisReportCreate,
    SynthesisReportResponse,
)
from app.services.base import BaseService


class MorningReportService:
    def __init__(self):
        self.base = BaseService[
            MorningReport, MorningReportCreate, MorningReportCreate, MorningReportResponse
        ](MorningReport, MorningReportResponse)

    async def list_with_date_range(
        self,
        db: AsyncSession,
        from_date: str | None = None,
        to: str | None = None,
        limit: int = 50,
    ) -> list[MorningReportListResponse]:
        query = select(MorningReport)
        if from_date:
            query = query.where(MorningReport.report_date >= from_date)
        if to:
            query = query.where(MorningReport.report_date <= to)
        query = query.order_by(MorningReport.report_date.desc()).limit(limit)
        result = await db.execute(query)
        return [MorningReportListResponse.model_validate(r) for r in result.scalars().all()]

    async def check_date_conflict(self, db: AsyncSession, report_date) -> bool:
        result = await db.execute(
            select(MorningReport).where(MorningReport.report_date == report_date)
        )
        return result.scalar_one_or_none() is not None

    async def get_latest(self, db: AsyncSession) -> MorningReport | None:
        result = await db.execute(
            select(MorningReport).order_by(MorningReport.report_date.desc()).limit(1)
        )
        return result.scalar_one_or_none()


class SynthesisReportService:
    def __init__(self):
        self.base = BaseService[
            SynthesisReport,
            SynthesisReportCreate,
            SynthesisReportCreate,
            SynthesisReportResponse,
        ](SynthesisReport, SynthesisReportResponse)

    async def list_recent(self, db: AsyncSession, limit: int = 50) -> list[SynthesisReportResponse]:
        reports = await self.base.list_all(
            db, order_by=SynthesisReport.created_at.desc(), limit=limit
        )
        return [SynthesisReportResponse.model_validate(r) for r in reports]
