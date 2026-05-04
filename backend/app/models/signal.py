import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Date, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    stock_id: Mapped[str] = mapped_column(String(36), ForeignKey("stocks.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[str] = mapped_column(String(4), nullable=False)
    intensity: Mapped[int] = mapped_column(Integer, nullable=False)
    core_thesis: Mapped[str] = mapped_column(Text, nullable=False)
    key_assumptions: Mapped[dict] = mapped_column(JSON, nullable=False)
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    stock: Mapped["Stock"] = relationship(lazy="joined")
    evolutions: Mapped[list["SignalEvolution"]] = relationship(back_populates="signal", cascade="all, delete-orphan")


class SignalEvolution(Base):
    __tablename__ = "signal_evolutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id: Mapped[str] = mapped_column(String(36), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    new_confidence: Mapped[str | None] = mapped_column(String(4))
    new_intensity: Mapped[int | None] = mapped_column(Integer)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    new_information_summary: Mapped[dict | None] = mapped_column(JSON)
    assumption_status: Mapped[dict | None] = mapped_column(JSON)
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    signal: Mapped["Signal"] = relationship(back_populates="evolutions")
