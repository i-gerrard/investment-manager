from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.portfolio import Holding, Portfolio
from app.models.stock import Stock
from app.models.user import User
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
    PortfolioCreate,
    PortfolioDetailResponse,
    PortfolioResponse,
    PortfolioUpdate,
)

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolios"])


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == current_user.id).order_by(Portfolio.created_at))
    portfolios = result.scalars().all()
    return [PortfolioResponse.model_validate(p) for p in portfolios]


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    body: PortfolioCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    portfolio = Portfolio(user_id=current_user.id, **body.model_dump())
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return PortfolioResponse.model_validate(portfolio)


@router.get("/{portfolio_id}", response_model=PortfolioDetailResponse)
async def get_portfolio(
    portfolio_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return PortfolioDetailResponse.model_validate(portfolio)


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: str,
    body: PortfolioUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(portfolio, key, val)
    await db.commit()
    await db.refresh(portfolio)
    return PortfolioResponse.model_validate(portfolio)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    await db.delete(portfolio)
    await db.commit()


# ── Holdings ──

@router.get("/{portfolio_id}/holdings", response_model=list[HoldingResponse])
async def list_holdings(
    portfolio_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    result = await db.execute(select(Holding).where(Holding.portfolio_id == portfolio_id).order_by(Holding.position_percent.desc()))
    return [HoldingResponse.model_validate(h) for h in result.scalars().all()]


@router.post("/{portfolio_id}/holdings", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
async def create_holding(
    portfolio_id: str,
    body: HoldingCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    result = await db.execute(select(Stock).where(Stock.id == body.stock_id))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")

    holding = Holding(portfolio_id=portfolio_id, ticker=stock.ticker, **body.model_dump())
    db.add(holding)
    await db.commit()
    await db.refresh(holding)
    return HoldingResponse.model_validate(holding)


@router.put("/{portfolio_id}/holdings/{holding_id}", response_model=HoldingResponse)
async def update_holding(
    portfolio_id: str,
    holding_id: str,
    body: HoldingUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Holding).where(Holding.id == holding_id, Holding.portfolio_id == portfolio_id)
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")

    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(holding, key, val)
    await db.commit()
    await db.refresh(holding)
    return HoldingResponse.model_validate(holding)


@router.delete("/{portfolio_id}/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    portfolio_id: str,
    holding_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Holding).where(Holding.id == holding_id, Holding.portfolio_id == portfolio_id)
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
    await db.delete(holding)
    await db.commit()
