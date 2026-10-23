from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.audit import AuditEvent


def log_audit_event(
    db: Session,
    entity_type: str,
    entity_id: str,
    action: str,
    actor_id: Optional[int] = None,
    reason: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """Record an immutable audit event in the database."""
    now = datetime.now(timezone.utc)
    event = AuditEvent(
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        actor_id=actor_id,
        event_time=now,
        reason=reason,
        details=details or {},
    )
    db.add(event)
    return event
