from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.research import ResearchReport
from app.models.user import User
from app.schemas.research import (
    CitationCreate,
    CitationResponse,
    ReportCreate,
    ReportListResponse,
    ReportResponse,
    ReportUpdate,
)
from app.services.research import CitationService, ResearchService

router = APIRouter(prefix="/api/v1/research", tags=["research"])
research_service = ResearchService()
citation_service = CitationService()


# ── Reports ──

@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    stock_id: Optional[str] = Query(None),
    phase: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    return await research_service.list_reports(
        db, stock_id=stock_id, phase=phase, q=q, page=page, limit=limit
    )


@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    body: ReportCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await research_service.verify_stock_exists(db, body.stock_id)
    return await research_service.base.create(db, body, user_id=current_user.id)


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    report = await research_service.base.get_or_404(db, ResearchReport.id == report_id)
    return ResearchReport.model_validate(report)


@router.put("/reports/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    body: ReportUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    report = await research_service.base.get_or_404(db, ResearchReport.id == report_id)
    return await research_service.base.update(db, report, body)


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    report = await research_service.base.get_or_404(db, ResearchReport.id == report_id)
    await research_service.base.delete(db, report)


# ── Citations ──

@router.get("/reports/{report_id}/citations", response_model=list[CitationResponse])
async def list_citations(report_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    return await citation_service.list_for_report(db, report_id)


@router.post("/reports/{report_id}/citations", response_model=CitationResponse, status_code=status.HTTP_201_CREATED)
async def add_citation(
    report_id: str,
    body: CitationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await research_service.base.get_or_404(db, ResearchReport.id == report_id)
    return await citation_service.base.create(db, body, research_report_id=report_id)


@router.post("/reports/{report_id}/citations/batch", response_model=list[CitationResponse], status_code=status.HTTP_201_CREATED)
async def batch_add_citations(
    report_id: str,
    body: list[CitationCreate],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await research_service.base.get_or_404(db, ResearchReport.id == report_id)
    return await citation_service.batch_create(db, report_id, body)
