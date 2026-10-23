from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class QualityRule(Base):
    __tablename__ = "quality_rule"

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    parameter_code: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    test_results: Mapped[list["QualityTestResult"]] = relationship("QualityTestResult", back_populates="rule")

    __table_args__ = (
        UniqueConstraint("name", "rule_version", name="uq_rule_version"),
        CheckConstraint(
            "parameter_code IN ('temperature', 'salinity', 'ph', 'dissolved_oxygen')",
            name="chk_rule_parameter_code",
        ),
        CheckConstraint(
            "rule_type IN ('range', 'gap', 'rate_of_change', 'stuck_sensor', 'duplicate')",
            name="chk_rule_type",
        ),
    )


class QualityTestResult(Base):
    __tablename__ = "quality_test_result"

    test_result_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    observation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("observation.observation_id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quality_rule.rule_id", ondelete="RESTRICT"), nullable=False
    )
    flag: Mapped[str] = mapped_column(String(16), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    observation: Mapped["Observation"] = relationship("Observation", back_populates="quality_results")
    rule: Mapped["QualityRule"] = relationship("QualityRule", back_populates="test_results")

    __table_args__ = (
        CheckConstraint(
            "flag IN ('pass', 'suspect', 'fail')",
            name="chk_quality_flag",
        ),
        Index("idx_quality_result_observation_tested", "observation_id", tested_at.desc()),
    )
