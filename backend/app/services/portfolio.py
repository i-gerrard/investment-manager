from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.portfolio import Holding, Portfolio
from app.models.stock import Stock
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioDetailResponse,
    PortfolioResponse,
)
from app.services.base import BaseService


class PortfolioService:
    def __init__(self):
        self.base = BaseService[Portfolio, PortfolioCreate, PortfolioUpdate, PortfolioResponse](
            Portfolio, PortfolioResponse
        )
        self.holding_base = BaseService[Holding, HoldingCreate, HoldingUpdate, HoldingResponse](
            Holding, HoldingResponse
        )

    async def list_for_user(self, db: AsyncSession, user_id: str) -> list[PortfolioResponse]:
        portfolios = await self.base.list_all(
            db, Portfolio.user_id == user_id, order_by=Portfolio.created_at
        )
        return [PortfolioResponse.model_validate(p) for p in portfolios]

    async def get_with_holdings(self, db: AsyncSession, portfolio_id: str, user_id: str) -> PortfolioDetailResponse:
        portfolio = await self.base.get_or_404(
            db,
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
            options=[selectinload(Portfolio.holdings).selectinload(Holding.stock)],
        )
        return PortfolioDetailResponse.model_validate(portfolio)

    async def get_holdings(self, db: AsyncSession, portfolio_id: str) -> list[HoldingResponse]:
        holdings = await self.holding_base.list_all(
            db,
            Holding.portfolio_id == portfolio_id,
            options=[selectinload(Holding.stock)],
            order_by=Holding.position_percent.desc(),
        )
        return [HoldingResponse.model_validate(h) for h in holdings]

    async def verify_portfolio_owner(self, db: AsyncSession, portfolio_id: str, user_id: str) -> Portfolio:
        return await self.base.get_or_404(
            db, Portfolio.id == portfolio_id, Portfolio.user_id == user_id
        )

    async def verify_stock_exists(self, db: AsyncSession, stock_id: str) -> Stock:
        result = await db.execute(select(Stock).where(Stock.id == stock_id))
        stock = result.scalar_one_or_none()
        if not stock:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")
        return stock
