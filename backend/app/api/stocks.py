from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stock import Stock
from app.schemas.stock import StockCreate, StockListResponse, StockResponse, StockUpdate
from app.services.stock import StockService

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])
stock_service = StockService()


@router.get("", response_model=StockListResponse)
async def list_stocks(
    db: Annotated[AsyncSession, Depends(get_db)],
    market: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    return await stock_service.search(db, market=market, q=q, page=page, limit=limit)


@router.post("", response_model=StockResponse, status_code=status.HTTP_201_CREATED)
async def create_stock(
    body: StockCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing = await stock_service.check_duplicate(db, body.ticker, body.market)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock {body.ticker} ({body.market}) already exists",
        )
    return await stock_service.base.create(db, body)


@router.get("/{stock_id}", response_model=StockResponse)
async def get_stock(stock_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    stock = await stock_service.base.get_or_404(db, Stock.id == stock_id)
    return stock_service.base.response_schema.model_validate(stock)


@router.put("/{stock_id}", response_model=StockResponse)
async def update_stock(
    stock_id: str,
    body: StockUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    stock = await stock_service.base.get_or_404(db, Stock.id == stock_id)
    return await stock_service.base.update(db, stock, body)


@router.delete("/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock(stock_id: str, db: Annotated[AsyncSession, Depends(get_db)]):
    stock = await stock_service.base.get_or_404(db, Stock.id == stock_id)
    await stock_service.base.delete(db, stock)
