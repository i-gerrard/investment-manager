#!/usr/bin/env python3
"""Bootstrap a development environment for the snapshot workflow.

Creates (idempotently):
  - dev user "dev" / "devpassword"
  - two portfolios: "eToro Ledger" and "TR Ledger"
  - BrokerPortfolioMapping rows linking each broker to its ledger

Run after backend has started at least once (so tables exist) or rely on
the create_all happening at app startup. Reads DATABASE_URL from env;
defaults to the SQLite file the backend uses.

Usage:
    cd backend && python ../scripts/seed_dev.py
"""

import asyncio
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app import models  # noqa: F401 — register tables
from app.database import Base
from app.models import User, Portfolio
from app.models.broker_sync import BrokerPortfolioMapping
from app.services.auth import pwd_context

DEV_USER = "dev"
DEV_PASS = "devpassword"

DEFAULT_DB = f"sqlite+aiosqlite:///{REPO / 'investr.db'}"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DB)


async def main() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        user = await _ensure_user(db)
        p_etoro = await _ensure_portfolio(db, user.id, "eToro Ledger")
        p_tr = await _ensure_portfolio(db, user.id, "TR Ledger")
        await _ensure_mapping(db, user.id, "etoro", p_etoro.id)
        await _ensure_mapping(db, user.id, "tr", p_tr.id)
        await db.commit()

    print(f"✓ Dev user ready: username={DEV_USER!r} password={DEV_PASS!r}")
    print(f"  eToro portfolio: {p_etoro.id}")
    print(f"  TR portfolio:    {p_tr.id}")
    print(f"  DB: {DATABASE_URL}")


async def _ensure_user(db: AsyncSession) -> User:
    existing = (await db.execute(select(User).where(User.username == DEV_USER))).scalar_one_or_none()
    if existing:
        return existing
    user = User(username=DEV_USER, password_hash=pwd_context.hash(DEV_PASS))
    db.add(user)
    await db.flush()
    return user


async def _ensure_portfolio(db: AsyncSession, user_id: str, name: str) -> Portfolio:
    existing = (await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id, Portfolio.name == name)
    )).scalar_one_or_none()
    if existing:
        return existing
    p = Portfolio(user_id=user_id, name=name)
    db.add(p)
    await db.flush()
    return p


async def _ensure_mapping(db: AsyncSession, user_id: str, broker: str, portfolio_id: str) -> None:
    existing = (await db.execute(
        select(BrokerPortfolioMapping).where(
            BrokerPortfolioMapping.user_id == user_id,
            BrokerPortfolioMapping.broker == broker,
        )
    )).scalar_one_or_none()
    if existing:
        if existing.portfolio_id != portfolio_id:
            existing.portfolio_id = portfolio_id
        return
    db.add(BrokerPortfolioMapping(user_id=user_id, broker=broker, portfolio_id=portfolio_id))


if __name__ == "__main__":
    asyncio.run(main())
