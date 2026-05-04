import uuid
from datetime import date, datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Date, func, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    stock_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("stocks.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    signal_rating: Mapped[str | None] = mapped_column(String(16))
    confidence: Mapped[str | None] = mapped_column(String(4))
    intensity: Mapped[int | None] = mapped_column(Integer, CheckConstraint("intensity >= 1 AND intensity <= 10"))
    core_thesis: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    stock: Mapped["Stock"] = relationship(lazy="joined")
    citations: Mapped[list["Citation"]] = relationship(back_populates="research_report", cascade="all, delete-orphan")


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_report_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("research_reports.id", ondelete="CASCADE"), nullable=False)
    author_org: Mapped[str] = mapped_column(String(256), nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date)
    source_title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048))
    quality_rating: Mapped[str] = mapped_column(String(2), nullable=False)
    claim_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    research_report: Mapped["ResearchReport"] = relationship(back_populates="citations")
