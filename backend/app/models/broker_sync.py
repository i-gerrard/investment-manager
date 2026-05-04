import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BrokerSyncLog(Base):
    """One record per sync attempt per broker."""
    __tablename__ = "broker_sync_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    broker: Mapped[str] = mapped_column(String(16), nullable=False)       # "etoro" | "tr" | "all"
    status: Mapped[str] = mapped_column(String(16), nullable=False)       # "running" | "success" | "failed" | "partial"
    positions_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    positions_synced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    portfolio_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True
    )
    error_msg: Mapped[Optional[str]] = mapped_column(Text)
    # JSON array of raw position objects captured from the browser
    raw_snapshot: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class BrokerPortfolioMapping(Base):
    """Maps each broker to the portfolio that receives its synced holdings."""
    __tablename__ = "broker_portfolio_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # "etoro" | "tr"
    broker: Mapped[str] = mapped_column(String(16), nullable=False)
    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    portfolio: Mapped["Portfolio"] = relationship(lazy="joined")
