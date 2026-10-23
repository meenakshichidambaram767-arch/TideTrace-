from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.ingestion import IngestionBatch, IngestionBatchResponse
from backend.app.models.user import UserAccount
from backend.app.api.v1.dependencies.auth import require_role
from backend.app.services.ingestion_service import process_ingestion_batch
from backend.app.core.errors import ValidationException

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.post("/batches", response_model=IngestionBatchResponse, status_code=status.HTTP_201_CREATED)
def ingest_batch_endpoint(
    batch: IngestionBatch,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    current_user: UserAccount = Depends(require_role("steward")),
    db: Session = Depends(get_db),
):
    """
    Ingest a batch of telemetry observations atomically and idempotently.
    
    Guarantees:
    - Replay of identical request returns cached result with 0 new inserts.
    - Reused idempotency key with modified payload returns 409 Conflict.
    - atomic=true rolls back newly inserted observations if any record is invalid.
    - Record-level duplicates on (source_system, source_message_id) are skipped and counted.
    """
    if len(batch.records) > 5000:
        raise ValidationException(
            message="Batch size exceeds maximum limit of 5,000 records.",
            code="BATCH_SIZE_EXCEEDED",
            details={"max_size": 5000, "provided_size": len(batch.records)},
        )

    return process_ingestion_batch(
        db=db,
        idempotency_key=idempotency_key,
        batch=batch,
        actor_id=current_user.user_id,
    )
