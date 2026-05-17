from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import Stock
from app.schemas.stock import StockCreate, StockUpdate, StockResponse, StockListResponse
from app.services.base import BaseService


class StockService:
    def __init__(self):
        self.base = BaseService[Stock, StockCreate, StockUpdate, StockResponse](Stock, StockResponse)

    async def search(
        self,
        db: AsyncSession,
        market: str | None = None,
        q: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> StockListResponse:
        query = select(Stock)
        count_query = select(func.count(Stock.id))
        if market:
            query = query.where(Stock.market == market)
            count_query = count_query.where(Stock.market == market)
        if q:
            search = f"%{q}%"
            query = query.where((Stock.ticker.ilike(search)) | (Stock.name.ilike(search)))
            count_query = count_query.where(
                (Stock.ticker.ilike(search)) | (Stock.name.ilike(search))
            )
        items, total = await self.base.paginate(
            db, query, count_query, page, limit, order_by=Stock.ticker
        )
        return StockListResponse(
            items=[StockResponse.model_validate(s) for s in items], total=total
        )

    async def check_duplicate(self, db: AsyncSession, ticker: str, market: str) -> Stock | None:
        result = await db.execute(
            select(Stock).where(Stock.ticker == ticker, Stock.market == market)
        )
        return result.scalar_one_or_none()

    async def ensure_stock(
        self, db: AsyncSession, *, ticker: str, name: str | None = None, market: str = "US"
    ) -> Stock:
        """Look up Stock by (ticker, market); create a minimal row if missing.
        Used by ingest paths (broker_sync, report_upload) that may encounter
        tickers not yet tracked.
        """
        result = await db.execute(
            select(Stock).where(Stock.ticker == ticker, Stock.market == market)
        )
        stock = result.scalar_one_or_none()
        if not stock:
            stock = Stock(ticker=ticker, name=name or ticker, market=market)
            db.add(stock)
            await db.flush()
        return stock
