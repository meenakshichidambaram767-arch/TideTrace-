from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.session import get_db
from backend.app.models.audit import AuditEvent
from backend.app.models.user import UserAccount
from backend.app.schemas.audit import AuditEventResponse
from backend.app.schemas.common import PaginatedResponse
from backend.app.api.v1.dependencies.auth import get_current_user

router = APIRouter(prefix="/audit-events", tags=["Audit Trail"])


@router.get("", response_model=PaginatedResponse[AuditEventResponse], status_code=status.HTTP_200_OK)
def search_audit_events(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    from_time: Optional[datetime] = Query(None),
    to_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search immutable audit trail events.
    Supports filtering by entity type, entity ID, and timestamp range with pagination.
    """
    query = db.query(AuditEvent)

    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditEvent.entity_id == str(entity_id))
    if from_time:
        query = query.filter(AuditEvent.event_time >= from_time)
    if to_time:
        query = query.filter(AuditEvent.event_time <= to_time)

    total = query.count()
    events = (
        query.order_by(desc(AuditEvent.event_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        AuditEventResponse(
            audit_id=e.audit_id,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            action=e.action,
            actor_id=e.actor_id,
            event_time=e.event_time,
            reason=e.reason,
            details=e.details,
        )
        for e in events
    ]

    return PaginatedResponse(items=items, page=page, page_size=page_size, total=total)
