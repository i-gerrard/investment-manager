from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.services.report import MorningReportService, SynthesisReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
morning_service = MorningReportService()
synthesis_service = SynthesisReportService()


# ── Morning Reports ──

@router.get("/morning", response_model=list[MorningReportListResponse])
async def list_morning_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
):
    return await morning_service.list_with_date_range(db, from_date=from_date, to=to)


@router.post("/morning", response_model=MorningReportResponse, status_code=status.HTTP_201_CREATED)
async def create_morning_report(
    body: MorningReportCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if await morning_service.check_date_conflict(db, body.report_date):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Report for {body.report_date} already exists",
        )
    return await morning_service.base.create(db, body)


@router.get("/morning/{report_id}", response_model=MorningReportResponse)
async def get_morning_report(report_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    report = await morning_service.base.get_or_404(db, MorningReport.id == report_id)
    return MorningReportResponse.model_validate(report)


@router.delete("/morning/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_morning_report(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    report = await morning_service.base.get_or_404(db, MorningReport.id == report_id)
    await morning_service.base.delete(db, report)


# ── Synthesis Reports ──

@router.get("/synthesis", response_model=list[SynthesisReportResponse])
async def list_synthesis_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await synthesis_service.list_recent(db)


@router.post("/synthesis", response_model=SynthesisReportResponse, status_code=status.HTTP_201_CREATED)
async def create_synthesis_report(
    body: SynthesisReportCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await synthesis_service.base.create(db, body, user_id=current_user.id)


@router.get("/synthesis/{report_id}", response_model=SynthesisReportResponse)
async def get_synthesis_report(report_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    report = await synthesis_service.base.get_or_404(db, SynthesisReport.id == report_id)
    return SynthesisReportResponse.model_validate(report)
