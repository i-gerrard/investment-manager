from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import Citation, ResearchReport
from app.schemas.research import (
    CitationCreate,
    CitationResponse,
    ReportCreate,
    ReportUpdate,
    ReportResponse,
    ReportListResponse,
)
from app.services.base import BaseService


class ResearchService:
    def __init__(self):
        self.base = BaseService[ResearchReport, ReportCreate, ReportUpdate, ReportResponse](
            ResearchReport, ReportResponse
        )

    async def list_reports(
        self,
        db: AsyncSession,
        stock_id: str | None = None,
        phase: str | None = None,
        q: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> ReportListResponse:
        query = select(ResearchReport)
        count_query = select(func.count(ResearchReport.id))
        if stock_id:
            query = query.where(ResearchReport.stock_id == stock_id)
            count_query = count_query.where(ResearchReport.stock_id == stock_id)
        if phase:
            query = query.where(ResearchReport.phase == phase)
            count_query = count_query.where(ResearchReport.phase == phase)
        if q:
            search = f"%{q}%"
            query = query.where(ResearchReport.title.ilike(search))
            count_query = count_query.where(ResearchReport.title.ilike(search))
        items, total = await self.base.paginate(
            db, query, count_query, page, limit, order_by=ResearchReport.created_at.desc()
        )
        return ReportListResponse(
            items=[ReportResponse.model_validate(r) for r in items], total=total
        )

    async def verify_stock_exists(self, db: AsyncSession, stock_id: str) -> None:
        from app.models.stock import Stock
        from fastapi import HTTPException, status

        result = await db.execute(select(Stock).where(Stock.id == stock_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")


class CitationService:
    def __init__(self):
        self.base = BaseService[Citation, CitationCreate, CitationCreate, CitationResponse](
            Citation, CitationResponse
        )

    async def list_for_report(self, db: AsyncSession, report_id: str) -> list[CitationResponse]:
        citations = await self.base.list_all(db, Citation.research_report_id == report_id)
        return [CitationResponse.model_validate(c) for c in citations]

    async def batch_create(
        self, db: AsyncSession, report_id: str, citations: list[CitationCreate]
    ) -> list[CitationResponse]:
        entities = [Citation(research_report_id=report_id, **c.model_dump()) for c in citations]
        db.add_all(entities)
        await db.commit()
        return [CitationResponse.model_validate(c) for c in entities]
