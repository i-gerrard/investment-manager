import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Stock(Base):
    __tablename__ = "stocks"
    __table_args__ = (UniqueConstraint("ticker", "market", name="uq_ticker_market"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(128))
    industry: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
