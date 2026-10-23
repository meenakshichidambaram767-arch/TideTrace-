from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserAccount(Base):
    __tablename__ = "user_account"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "role IN ('researcher', 'reviewer', 'steward', 'admin')",
            name="chk_user_role",
        ),
    )
