from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisRun(Base):
    __tablename__ = "analysis_run"

    analysis_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    analysis_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric: Mapped[str] = mapped_column(String(32), nullable=False)
    query_version: Mapped[str] = mapped_column(String(64), nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_account.user_id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    creator: Mapped["UserAccount"] = relationship("UserAccount")
    manifest_inputs: Mapped[List["AnalysisInput"]] = relationship(
        "AnalysisInput", back_populates="analysis", cascade="all, delete-orphan"
    )
    results: Mapped[List["AnalysisResult"]] = relationship(
        "AnalysisResult", back_populates="analysis", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "metric IN ('mean', 'min', 'max', 'count', 'median', 'standard_deviation')",
            name="chk_analysis_metric",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="chk_analysis_status",
        ),
    )


class AnalysisInput(Base):
    __tablename__ = "analysis_input"

    analysis_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), primary_key=True
    )
    observation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("observation.observation_id", ondelete="RESTRICT"), primary_key=True
    )
    revision_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("observation_revision.revision_id", ondelete="RESTRICT"), nullable=True
    )
    input_role: Mapped[str] = mapped_column(String(32), default="primary", nullable=False)

    analysis: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="manifest_inputs")
    observation: Mapped["Observation"] = relationship("Observation")
    revision: Mapped[Optional["ObservationRevision"]] = relationship("ObservationRevision")

    __table_args__ = (
        Index("idx_analysis_input_revision", "revision_id"),
    )


class AnalysisResult(Base):
    __tablename__ = "analysis_result"

    result_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_value: Mapped[Decimal] = mapped_column(Numeric(16, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    analysis: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="results")
