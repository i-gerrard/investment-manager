from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
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
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolios"])
portfolio_service = PortfolioService()


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await portfolio_service.list_for_user(db, current_user.id)


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    body: PortfolioCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await portfolio_service.base.create(db, body, user_id=current_user.id)


@router.get("/{portfolio_id}", response_model=PortfolioDetailResponse)
async def get_portfolio(
    portfolio_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await portfolio_service.get_with_holdings(db, portfolio_id, current_user.id)


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: str,
    body: PortfolioUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    portfolio = await portfolio_service.verify_portfolio_owner(db, portfolio_id, current_user.id)
    return await portfolio_service.base.update(db, portfolio, body)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    portfolio = await portfolio_service.verify_portfolio_owner(db, portfolio_id, current_user.id)
    await portfolio_service.base.delete(db, portfolio)


# ── Holdings ──

@router.get("/{portfolio_id}/holdings", response_model=list[HoldingResponse])
async def list_holdings(
    portfolio_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await portfolio_service.verify_portfolio_owner(db, portfolio_id, current_user.id)
    return await portfolio_service.get_holdings(db, portfolio_id)


@router.post("/{portfolio_id}/holdings", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
async def create_holding(
    portfolio_id: str,
    body: HoldingCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await portfolio_service.verify_portfolio_owner(db, portfolio_id, current_user.id)
    stock = await portfolio_service.verify_stock_exists(db, body.stock_id)
    return await portfolio_service.holding_base.create(
        db, body, portfolio_id=portfolio_id, ticker=stock.ticker
    )


@router.put("/{portfolio_id}/holdings/{holding_id}", response_model=HoldingResponse)
async def update_holding(
    portfolio_id: str,
    holding_id: str,
    body: HoldingUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await portfolio_service.verify_portfolio_owner(db, portfolio_id, current_user.id)
    holding = await portfolio_service.holding_base.get_or_404(
        db, portfolio_service.holding_base.model.id == holding_id,
        portfolio_service.holding_base.model.portfolio_id == portfolio_id,
    )
    return await portfolio_service.holding_base.update(db, holding, body)


@router.delete("/{portfolio_id}/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    portfolio_id: str,
    holding_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await portfolio_service.verify_portfolio_owner(db, portfolio_id, current_user.id)
    holding = await portfolio_service.holding_base.get_or_404(
        db, portfolio_service.holding_base.model.id == holding_id,
        portfolio_service.holding_base.model.portfolio_id == portfolio_id,
    )
    await portfolio_service.holding_base.delete(db, holding)
