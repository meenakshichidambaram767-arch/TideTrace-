from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditEvent(Base):
    __tablename__ = "audit_event"

    audit_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user_account.user_id", ondelete="SET NULL"), nullable=True
    )
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    actor: Mapped[Optional["UserAccount"]] = relationship("UserAccount")

    __table_args__ = (
        Index("idx_audit_event_lookup", "entity_type", "entity_id", event_time.desc()),
    )
