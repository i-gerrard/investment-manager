import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, DateTime, Date, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


class MacroSignal(Base):
    __tablename__ = "macro_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    signal_name: Mapped[str] = mapped_column(String(256), nullable=False)
    current_status: Mapped[str | None] = mapped_column(Text)
    mechanism: Mapped[str | None] = mapped_column(Text)
    impact_direction: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    related_stocks: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
