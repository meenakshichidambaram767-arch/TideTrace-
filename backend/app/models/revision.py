from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal
from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Text,
    Numeric,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ObservationRevision(Base):
    __tablename__ = "observation_revision"

    revision_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    observation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("observation.observation_id", ondelete="RESTRICT"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_account.user_id", ondelete="RESTRICT"), nullable=False
    )
    calibration_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("calibration.calibration_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    observation: Mapped["Observation"] = relationship("Observation", back_populates="revisions")
    reviewer: Mapped["UserAccount"] = relationship("UserAccount")
    calibration: Mapped[Optional["Calibration"]] = relationship("Calibration")

    __table_args__ = (
        UniqueConstraint("observation_id", "revision_number", name="uq_observation_revision_number"),
        CheckConstraint("revision_number >= 1", name="chk_revision_number_positive"),
        CheckConstraint(
            "decision IN ('accepted', 'corrected', 'rejected', 'needs_review')",
            name="chk_revision_decision",
        ),
        CheckConstraint("LENGTH(reason) >= 5", name="chk_revision_min_reason_length"),
        Index("idx_observation_revision_obs_rev", "observation_id", revision_number.desc()),
    )
