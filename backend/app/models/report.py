import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Date, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MorningReport(Base):
    __tablename__ = "morning_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    headline: Mapped[str | None] = mapped_column(String(512))
    key_themes: Mapped[dict | None] = mapped_column(JSONB)
    macro_signals: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sector_recommendations: Mapped[list["SectorRecommendation"]] = relationship(back_populates="morning_report", cascade="all, delete-orphan")


class SynthesisReport(Base):
    __tablename__ = "synthesis_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    thematic_clusters: Mapped[dict | None] = mapped_column(JSONB)
    risk_factors: Mapped[dict | None] = mapped_column(JSONB)
    signal_rating: Mapped[str | None] = mapped_column(String(16))
    confidence: Mapped[str | None] = mapped_column(String(4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SectorRecommendation(Base):
    __tablename__ = "sector_recommendations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    morning_report_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("morning_reports.id", ondelete="CASCADE"), nullable=False)
    sector_name: Mapped[str] = mapped_column(String(256), nullable=False)
    time_horizon: Mapped[str | None] = mapped_column(String(128))
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False)
    catalysts: Mapped[dict | None] = mapped_column(JSONB)
    risks: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    morning_report: Mapped["MorningReport"] = relationship(back_populates="sector_recommendations")
    stock_cards: Mapped[list["StockCard"]] = relationship(back_populates="sector_recommendation", cascade="all, delete-orphan")


class StockCard(Base):
    __tablename__ = "stock_cards"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    sector_recommendation_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("sector_recommendations.id", ondelete="CASCADE"), nullable=False)
    stock_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("stocks.id", ondelete="RESTRICT"), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    logic_analysis: Mapped[str | None] = mapped_column(Text)
    operation_advice: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sector_recommendation: Mapped["SectorRecommendation"] = relationship(back_populates="stock_cards")
    stock: Mapped["Stock"] = relationship(lazy="joined")
