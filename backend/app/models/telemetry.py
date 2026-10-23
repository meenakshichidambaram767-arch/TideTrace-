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
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_key"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    request_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    response_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="chk_idempotency_status",
        ),
    )


class Observation(Base):
    __tablename__ = "observation"

    observation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sensor.sensor_id", ondelete="RESTRICT"), nullable=False
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    parameter_code: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    source_message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="observations")
    quality_results: Mapped[List["QualityTestResult"]] = relationship("QualityTestResult", back_populates="observation", cascade="all, delete-orphan")
    revisions: Mapped[List["ObservationRevision"]] = relationship("ObservationRevision", back_populates="observation")

    __table_args__ = (
        UniqueConstraint("source_system", "source_message_id", name="uq_observation_source_message"),
        CheckConstraint(
            "parameter_code IN ('temperature', 'salinity', 'ph', 'dissolved_oxygen')",
            name="chk_observation_parameter_code",
        ),
        Index("idx_observation_sensor_time", "sensor_id", event_time.desc()),
        Index("idx_observation_parameter_time", "parameter_code", event_time.desc()),
    )
