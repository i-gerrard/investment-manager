from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.stock import Stock
from app.models.user import User
from app.schemas.stock import StockCreate, StockListResponse, StockResponse, StockUpdate

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])


@router.get("", response_model=StockListResponse)
async def list_stocks(
    db: Annotated[AsyncSession, Depends(get_db)],
    market: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    query = select(Stock)
    count_query = select(func.count(Stock.id))

    if market:
        query = query.where(Stock.market == market)
        count_query = count_query.where(Stock.market == market)
    if q:
        search = f"%{q}%"
        query = query.where((Stock.ticker.ilike(search)) | (Stock.name.ilike(search)))
        count_query = count_query.where((Stock.ticker.ilike(search)) | (Stock.name.ilike(search)))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * limit
    query = query.order_by(Stock.ticker).offset(offset).limit(limit)
    result = await db.execute(query)
    stocks = result.scalars().all()

    return StockListResponse(items=[StockResponse.model_validate(s) for s in stocks], total=total)


@router.post("", response_model=StockResponse, status_code=status.HTTP_201_CREATED)
async def create_stock(
    body: StockCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    result = await db.execute(
        select(Stock).where(Stock.ticker == body.ticker, Stock.market == body.market)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Stock {body.ticker} ({body.market}) already exists")

    stock = Stock(**body.model_dump())
    db.add(stock)
    await db.commit()
    await db.refresh(stock)
    return StockResponse.model_validate(stock)


@router.get("/{stock_id}", response_model=StockResponse)
async def get_stock(
    stock_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Stock).where(Stock.id == stock_id))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")
    return StockResponse.model_validate(stock)


@router.put("/{stock_id}", response_model=StockResponse)
async def update_stock(
    stock_id: str,
    body: StockUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    result = await db.execute(select(Stock).where(Stock.id == stock_id))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")

    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(stock, key, val)
    await db.commit()
    await db.refresh(stock)
    return StockResponse.model_validate(stock)


@router.delete("/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stock(
    stock_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    result = await db.execute(select(Stock).where(Stock.id == stock_id))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")
    await db.delete(stock)
    await db.commit()
