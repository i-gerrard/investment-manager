from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.research import Citation, ResearchReport
from app.models.stock import Stock
from app.models.user import User
from app.schemas.research import (
    CitationCreate,
    CitationResponse,
    ReportCreate,
    ReportListResponse,
    ReportResponse,
    ReportUpdate,
)

router = APIRouter(prefix="/api/v1/research", tags=["research"])


# ── Reports ──

@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    stock_id: str | None = Query(None),
    phase: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    _: Annotated[User | None, Depends(get_current_user)] = None,
):
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

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * limit
    query = query.order_by(ResearchReport.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    reports = result.scalars().all()

    return ReportListResponse(items=[ReportResponse.model_validate(r) for r in reports], total=total)


@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    body: ReportCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Stock).where(Stock.id == body.stock_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")

    report = ResearchReport(user_id=current_user.id, **body.model_dump())
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return ReportResponse.model_validate(report)


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(ResearchReport).where(ResearchReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ReportResponse.model_validate(report)


@router.put("/reports/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    body: ReportUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(ResearchReport).where(ResearchReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(report, key, val)
    await db.commit()
    await db.refresh(report)
    return ReportResponse.model_validate(report)


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(ResearchReport).where(ResearchReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    await db.delete(report)
    await db.commit()


# ── Citations ──

@router.get("/reports/{report_id}/citations", response_model=list[CitationResponse])
async def list_citations(report_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Citation).where(Citation.research_report_id == report_id))
    return [CitationResponse.model_validate(c) for c in result.scalars().all()]


@router.post("/reports/{report_id}/citations", response_model=CitationResponse, status_code=status.HTTP_201_CREATED)
async def add_citation(
    report_id: str,
    body: CitationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(ResearchReport).where(ResearchReport.id == report_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    citation = Citation(research_report_id=report_id, **body.model_dump())
    db.add(citation)
    await db.commit()
    await db.refresh(citation)
    return CitationResponse.model_validate(citation)


@router.post("/reports/{report_id}/citations/batch", response_model=list[CitationResponse], status_code=status.HTTP_201_CREATED)
async def batch_add_citations(
    report_id: str,
    body: list[CitationCreate],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(ResearchReport).where(ResearchReport.id == report_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    citations = [Citation(research_report_id=report_id, **c.model_dump()) for c in body]
    db.add_all(citations)
    await db.commit()
    return [CitationResponse.model_validate(c) for c in citations]
