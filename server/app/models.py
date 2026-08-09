"""SQLAlchemy models. create_all() on startup — no Alembic for the 48h build (documented tradeoff)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AnalysisStatus(str, enum.Enum):
    queued = "queued"
    cloning = "cloning"
    scanning = "scanning"
    reasoning = "reasoning"
    generating = "generating"
    validating = "validating"
    done = "done"
    failed = "failed"


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    repo_url: Mapped[str] = mapped_column(Text)
    head_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.queued
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    facts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    services: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    zerops_yaml: Mapped[str | None] = mapped_column(Text, nullable=True)
    checklist: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ChecklistState(Base):
    __tablename__ = "checklist_state"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id"), primary_key=True
    )
    step_id: Mapped[str] = mapped_column(String, primary_key=True)
    checked: Mapped[bool] = mapped_column(Boolean, default=False)
