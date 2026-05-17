from typing import Optional
import uuid
from datetime import date, datetime

from sqlalchemy import String, Float, Date, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="portfolios")
    holdings: Mapped[list["Holding"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioSnapshot(Base):
    """Account-level daily aggregate. One row per (user, report_date).

    Written by both broker_sync ingest and HTML report upload. The `source`
    column records which path produced the row.
    """
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "report_date", name="uq_snapshot_user_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # eToro side (USD)
    etoro_total_usd: Mapped[Optional[float]] = mapped_column(Float)
    etoro_cash_usd: Mapped[Optional[float]] = mapped_column(Float)
    etoro_invested_usd: Mapped[Optional[float]] = mapped_column(Float)
    etoro_pnl_day_usd: Mapped[Optional[float]] = mapped_column(Float)

    # Trade Republic side (EUR)
    tr_total_eur: Mapped[Optional[float]] = mapped_column(Float)
    tr_cash_eur: Mapped[Optional[float]] = mapped_column(Float)
    tr_invested_eur: Mapped[Optional[float]] = mapped_column(Float)
    tr_pnl_day_eur: Mapped[Optional[float]] = mapped_column(Float)

    # Cross-account
    eur_usd_rate: Mapped[Optional[float]] = mapped_column(Float)
    combined_total_usd: Mapped[Optional[float]] = mapped_column(Float)
    combined_cash_usd: Mapped[Optional[float]] = mapped_column(Float)
    cash_ratio_pct: Mapped[Optional[float]] = mapped_column(Float)

    # Provenance
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # 'broker_sync' | 'report_upload' | 'manual'
    raw_html: Mapped[Optional[str]] = mapped_column(Text)  # populated when source='report_upload'

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    holdings: Mapped[list["Holding"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "account", "ticker", name="uq_holding_snapshot_account_ticker"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    snapshot_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("portfolio_snapshots.id", ondelete="CASCADE"), nullable=True, index=True
    )
    stock_id: Mapped[str] = mapped_column(String(36), ForeignKey("stocks.id", ondelete="RESTRICT"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    # Snapshot dimension
    snapshot_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    account: Mapped[Optional[str]] = mapped_column(String(16))  # 'etoro' | 'tr' | 'manual'

    # Position fields (promoted from broker_sync notes JSON; cost_basis renamed -> avg_cost)
    shares: Mapped[Optional[float]] = mapped_column(Float)
    avg_cost: Mapped[Optional[float]] = mapped_column(Float)
    current_price: Mapped[Optional[float]] = mapped_column(Float)
    market_value_usd: Mapped[Optional[float]] = mapped_column(Float)
    pnl_total_usd: Mapped[Optional[float]] = mapped_column(Float)
    pnl_total_pct: Mapped[Optional[float]] = mapped_column(Float)
    pnl_day_pct: Mapped[Optional[float]] = mapped_column(Float)
    position_percent: Mapped[Optional[float]] = mapped_column(Float)

    # Report verdict (optional, populated by HTML report parser)
    verdict: Mapped[Optional[str]] = mapped_column(String(10))  # 'buy' | 'hold' | 'sell'

    # Existing
    entry_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")
    snapshot: Mapped[Optional["PortfolioSnapshot"]] = relationship(back_populates="holdings")
    stock: Mapped["Stock"] = relationship(lazy="joined")
