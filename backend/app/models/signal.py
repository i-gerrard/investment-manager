import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Date, func, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    stock_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("stocks.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[str] = mapped_column(String(4), nullable=False)
    intensity: Mapped[int] = mapped_column(Integer, CheckConstraint("intensity >= 1 AND intensity <= 10"), nullable=False)
    core_thesis: Mapped[str] = mapped_column(Text, nullable=False)
    key_assumptions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    stock: Mapped["Stock"] = relationship(lazy="joined")
    evolutions: Mapped[list["SignalEvolution"]] = relationship(back_populates="signal", cascade="all, delete-orphan")


class SignalEvolution(Base):
    __tablename__ = "signal_evolutions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    new_confidence: Mapped[str | None] = mapped_column(String(4))
    new_intensity: Mapped[int | None] = mapped_column(Integer, CheckConstraint("intensity >= 1 AND intensity <= 10"))
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    new_information_summary: Mapped[dict | None] = mapped_column(JSONB)
    assumption_status: Mapped[dict | None] = mapped_column(JSONB)
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    signal: Mapped["Signal"] = relationship(back_populates="evolutions")
