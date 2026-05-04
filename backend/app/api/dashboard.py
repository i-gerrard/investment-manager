from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.portfolio import Portfolio, Holding
from app.models.research import ResearchReport
from app.models.report import MorningReport

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Portfolio summary
    portfolios_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id).order_by(Portfolio.created_at)
    )
    portfolios = portfolios_result.scalars().all()
    portfolio_summaries = []
    for p in portfolios:
        hr = await db.execute(select(func.count(Holding.id)).where(Holding.portfolio_id == p.id))
        holding_count = hr.scalar()
        portfolio_summaries.append({
            "id": p.id,
            "name": p.name,
            "holding_count": holding_count,
        })

    # Recent research reports
    reports_result = await db.execute(
        select(ResearchReport)
        .where(ResearchReport.user_id == current_user.id)
        .order_by(ResearchReport.created_at.desc())
        .limit(5)
    )
    recent_reports = [
        {"id": r.id, "title": r.title, "phase": r.phase, "signal_rating": r.signal_rating, "created_at": str(r.created_at)}
        for r in reports_result.scalars().all()
    ]

    # Latest morning report
    mr_result = await db.execute(
        select(MorningReport).order_by(MorningReport.report_date.desc()).limit(1)
    )
    latest_morning = mr_result.scalar_one_or_none()
    latest_morning_summary = None
    if latest_morning:
        latest_morning_summary = {
            "id": latest_morning.id,
            "report_date": str(latest_morning.report_date),
            "headline": latest_morning.headline,
        }

    return {
        "portfolios": portfolio_summaries,
        "recent_reports": recent_reports,
        "latest_morning_report": latest_morning_summary,
    }
