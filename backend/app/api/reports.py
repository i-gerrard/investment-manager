from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.report import MorningReport, SynthesisReport
from app.models.user import User
from app.schemas.report import (
    MorningReportCreate,
    MorningReportListResponse,
    MorningReportResponse,
    SynthesisReportCreate,
    SynthesisReportResponse,
)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


# ── Morning Reports ──

@router.get("/morning", response_model=list[MorningReportListResponse])
async def list_morning_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    query = select(MorningReport)
    if from_date:
        query = query.where(MorningReport.report_date >= from_date)
    if to:
        query = query.where(MorningReport.report_date <= to)
    query = query.order_by(MorningReport.report_date.desc()).limit(50)
    result = await db.execute(query)
    return [MorningReportListResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/morning", response_model=MorningReportResponse, status_code=status.HTTP_201_CREATED)
async def create_morning_report(
    body: MorningReportCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(MorningReport).where(MorningReport.report_date == body.report_date))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Report for {body.report_date} already exists")

    report = MorningReport(**body.model_dump())
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return MorningReportResponse.model_validate(report)


@router.get("/morning/{report_id}", response_model=MorningReportResponse)
async def get_morning_report(report_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(MorningReport).where(MorningReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return MorningReportResponse.model_validate(report)


@router.delete("/morning/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_morning_report(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(MorningReport).where(MorningReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    await db.delete(report)
    await db.commit()


# ── Synthesis Reports ──

@router.get("/synthesis", response_model=list[SynthesisReportResponse])
async def list_synthesis_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(SynthesisReport).order_by(SynthesisReport.created_at.desc()).limit(50)
    )
    return [SynthesisReportResponse.model_validate(r) for r in result.scalars().all()]


@router.post("/synthesis", response_model=SynthesisReportResponse, status_code=status.HTTP_201_CREATED)
async def create_synthesis_report(
    body: SynthesisReportCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    report = SynthesisReport(user_id=current_user.id, **body.model_dump())
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return SynthesisReportResponse.model_validate(report)


@router.get("/synthesis/{report_id}", response_model=SynthesisReportResponse)
async def get_synthesis_report(report_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(SynthesisReport).where(SynthesisReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return SynthesisReportResponse.model_validate(report)
