import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Date, func, DECIMAL, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SentimentScore(Base):
    __tablename__ = "sentiment_scores"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    stock_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("stocks.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_headline: Mapped[str] = mapped_column(String(1024), nullable=False)
    score: Mapped[float] = mapped_column(DECIMAL(4, 2), CheckConstraint("score >= -1.0 AND score <= 1.0"), nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    key_driver: Mapped[str | None] = mapped_column(Text)
    scored_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    stock: Mapped["Stock"] = relationship(lazy="joined")


class SentimentAggregate(Base):
    __tablename__ = "sentiment_aggregates"
    __table_args__ = (UniqueConstraint("stock_id", "date", name="uq_sentiment_agg_stock_date"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    stock_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("stocks.id", ondelete="RESTRICT"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    overall_score: Mapped[float | None] = mapped_column(DECIMAL(4, 2))
    dominant_tone: Mapped[str | None] = mapped_column(String(32))
    bullish_drivers: Mapped[dict | None] = mapped_column(JSONB)
    bearish_drivers: Mapped[dict | None] = mapped_column(JSONB)
    confidence: Mapped[str | None] = mapped_column(String(4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    stock: Mapped["Stock"] = relationship(lazy="joined")
