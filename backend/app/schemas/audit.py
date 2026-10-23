from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    audit_id: int
    entity_type: str
    entity_id: str
    action: str
    actor_id: Optional[int]
    event_time: datetime
    reason: Optional[str]
    details: Dict[str, Any]
