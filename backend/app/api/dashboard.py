from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.report import MorningReportService
from app.services.research import ResearchService
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
portfolio_service = PortfolioService()
research_service = ResearchService()
morning_service = MorningReportService()


@router.get("")
async def dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    portfolios = await portfolio_service.list_for_user(db, current_user.id)
    portfolio_summaries = []
    for p in portfolios:
        holdings = await portfolio_service.get_holdings(db, p.id)
        portfolio_summaries.append({
            "id": p.id,
            "name": p.name,
            "holding_count": len(holdings),
        })

    reports_result = await research_service.list_reports(db, limit=5)
    recent_reports = [
        {
            "id": r.id,
            "title": r.title,
            "phase": r.phase,
            "signal_rating": r.signal_rating,
            "created_at": str(r.created_at),
        }
        for r in reports_result.items
    ]

    latest_morning = await morning_service.get_latest(db)
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
