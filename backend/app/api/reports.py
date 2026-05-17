from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.broker_sync import BrokerPortfolioMapping
from app.models.report import MorningReport, SynthesisReport
from app.models.user import User
from app.schemas.report import (
    MorningReportCreate,
    MorningReportListResponse,
    MorningReportResponse,
    ReportUploadRequest,
    ReportUploadResponse,
    SynthesisReportCreate,
    SynthesisReportResponse,
)
from app.services.recommendation_writer import persist_recommendations
from app.services.report import MorningReportService, SynthesisReportService
from app.services.report_parser import parse_report
from app.services.snapshot_writer import write_snapshot

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


# ── HTML Report Upload (Phase B) ──

@router.post("/upload", response_model=ReportUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_report(
    body: ReportUploadRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Parse a us-stock-report HTML and persist as a daily snapshot.

    Idempotent on (user_id, report_date): re-uploading the same date replaces
    the snapshot's holdings and refreshes the MorningReport HTML backup.
    Recommendations are parsed but not yet persisted (Phase C).
    """
    parsed = parse_report(body.html, report_date=body.report_date)
    if parsed.report_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not determine report_date from HTML; supply it explicitly.",
        )

    mappings = await _resolve_account_mappings(db, current_user.id)
    if not mappings:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No broker portfolio mappings configured. "
                   "Create them via POST /api/v1/broker-sync/mappings first.",
        )

    morning = await _upsert_morning_report(db, parsed.report_date, body.html)

    snapshot = await write_snapshot(
        db,
        user_id=current_user.id,
        report_date=parsed.report_date,
        source="report_upload",
        summary=parsed.summary,
        holdings=parsed.holdings,
        account_to_portfolio=mappings,
        raw_html=None,  # already backed up in morning_report.html_content
    )

    persisted_recs, skipped_recs = await persist_recommendations(
        db,
        morning_report_id=morning.id,
        report_date=parsed.report_date,
        recommendations=parsed.recommendations,
    )

    await db.commit()

    skipped_holdings = sum(1 for h in parsed.holdings if h.account not in mappings)
    return ReportUploadResponse(
        snapshot_id=snapshot.id,
        morning_report_id=morning.id,
        report_date=parsed.report_date,
        source=snapshot.source,
        holdings_count=len(parsed.holdings) - skipped_holdings,
        recommendations_parsed=len(parsed.recommendations),
        recommendations_persisted=persisted_recs,
        skipped_holdings=skipped_holdings,
        skipped_recommendations=skipped_recs,
    )


# ── Upload helpers ──

async def _resolve_account_mappings(db: AsyncSession, user_id: str) -> dict[str, str]:
    """Build {'etoro': portfolio_id, 'tr': portfolio_id} from BrokerPortfolioMapping."""
    result = await db.execute(
        select(BrokerPortfolioMapping).where(BrokerPortfolioMapping.user_id == user_id)
    )
    return {m.broker: m.portfolio_id for m in result.scalars().all()}


async def _upsert_morning_report(db: AsyncSession, report_date, html: str) -> MorningReport:
    """Find-or-create MorningReport for a date; refresh html_content on conflict."""
    existing = (await db.execute(
        select(MorningReport).where(MorningReport.report_date == report_date)
    )).scalar_one_or_none()
    if existing:
        existing.html_content = html
        await db.flush()
        return existing
    mr = MorningReport(report_date=report_date, html_content=html)
    db.add(mr)
    await db.flush()
    return mr
