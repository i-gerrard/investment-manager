"""Trade-review entities: tracks whether report recommendations were
executed, skipped, or replayed as a what-if simulation.

Both Execution and Simulation reference stock_cards.id (recommendation row).
The paper-trading sandbox (SimulatedPortfolio in simulation.py) is a
separate, unrelated subsystem.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Execution(Base):
    """Records the user's actual response to a recommendation:
    executed, skipped, or partially executed.
    """
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recommendation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stock_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 'executed' | 'skipped' | 'partial'
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    actual_price: Mapped[Optional[float]] = mapped_column(Float)
    actual_shares: Mapped[Optional[float]] = mapped_column(Float)
    execution_date: Mapped[Optional[date]] = mapped_column(Date)
    # 'forgot' | 'disagreed' | 'no_cash' | 'waiting_better_price' | 'other'
    skip_reason: Mapped[Optional[str]] = mapped_column(String(50))
    skip_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    recommendation: Mapped["StockCard"] = relationship(back_populates="executions")


class Simulation(Base):
    """What-if replay of a recommendation: assume entry at price X on date D,
    compute theoretical pnl, compare to actual execution to derive regret.
    """
    __tablename__ = "simulations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recommendation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stock_cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sim_entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    sim_entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    sim_entry_shares: Mapped[float] = mapped_column(Float, nullable=False)
    sim_exit_price: Mapped[Optional[float]] = mapped_column(Float)
    sim_exit_date: Mapped[Optional[date]] = mapped_column(Date)  # NULL = still holding

    # Stored (not derived) so the review page can sort/aggregate cheaply
    sim_pnl_usd: Mapped[Optional[float]] = mapped_column(Float)
    sim_pnl_pct: Mapped[Optional[float]] = mapped_column(Float)
    actual_pnl_usd: Mapped[Optional[float]] = mapped_column(Float)
    regret_usd: Mapped[Optional[float]] = mapped_column(Float)  # sim_pnl - actual_pnl

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recommendation: Mapped["StockCard"] = relationship(back_populates="simulations")
