import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SimulatedPortfolio(Base):
    __tablename__ = "simulated_portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    initial_capital: Mapped[float] = mapped_column(Float, nullable=False)
    cash_balance: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    # CFD max leverage allowed (e.g. 10.0 = up to 10x)
    max_leverage: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    # Margin call triggers when equity / total_margin < this rate
    maintenance_margin_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    positions: Mapped[list["SimulatedPosition"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    trades: Mapped[list["SimulatedTrade"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["TradeReview"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class SimulatedPosition(Base):
    __tablename__ = "simulated_positions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulated_portfolios.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("stocks.id", ondelete="SET NULL"), nullable=True
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # LONG / SHORT
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    avg_entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    leverage_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    # Cash locked as margin = notional_value / leverage_ratio
    margin_used: Mapped[float] = mapped_column(Float, nullable=False)
    # Total exposure = quantity * avg_entry_price
    notional_value: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float)
    take_profit: Mapped[Optional[float]] = mapped_column(Float)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    portfolio: Mapped["SimulatedPortfolio"] = relationship(back_populates="positions")
    stock: Mapped[Optional["Stock"]] = relationship(lazy="joined")


class SimulatedTrade(Base):
    __tablename__ = "simulated_trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulated_portfolios.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("stocks.id", ondelete="SET NULL"), nullable=True
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    # BUY_LONG | SELL_LONG | SELL_SHORT | BUY_SHORT
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    leverage_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    margin_used: Mapped[float] = mapped_column(Float, nullable=False)
    notional_value: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    # MANUAL | AI_SIGNAL | RESEARCH
    triggered_by: Mapped[str] = mapped_column(String(16), nullable=False, default="MANUAL")
    signal_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("signals.id", ondelete="SET NULL"), nullable=True
    )
    stop_loss: Mapped[Optional[float]] = mapped_column(Float)
    take_profit: Mapped[Optional[float]] = mapped_column(Float)
    # Populated when closing a position
    realized_pnl: Mapped[Optional[float]] = mapped_column(Float)
    fees: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    portfolio: Mapped["SimulatedPortfolio"] = relationship(back_populates="trades")
    stock: Mapped[Optional["Stock"]] = relationship(lazy="joined")
    review: Mapped[Optional["TradeReview"]] = relationship(back_populates="trade", uselist=False)


class TradeReview(Base):
    __tablename__ = "trade_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulated_portfolios.id", ondelete="CASCADE"), nullable=False
    )
    trade_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("simulated_trades.id", ondelete="SET NULL"), nullable=True
    )
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    entry_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    actual_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    pnl_realized: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lessons_learned: Mapped[Optional[str]] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=3)  # 1-5
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    portfolio: Mapped["SimulatedPortfolio"] = relationship(back_populates="reviews")
    trade: Mapped[Optional["SimulatedTrade"]] = relationship(back_populates="review")
