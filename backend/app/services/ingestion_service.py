import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.models.telemetry import Observation, IdempotencyKey
from backend.app.models.registry import Sensor
from backend.app.schemas.ingestion import IngestionBatch, IngestionBatchResponse, BatchRecordError
from backend.app.core.errors import ConflictException, ValidationException
from backend.app.services.audit_service import log_audit_event


def compute_payload_hash(batch: IngestionBatch) -> str:
    """Compute a deterministic SHA-256 hash of the ingestion batch payload."""
    serialized = json.dumps(batch.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def process_ingestion_batch(
    db: Session,
    idempotency_key: str,
    batch: IngestionBatch,
    actor_id: Optional[int] = None,
) -> IngestionBatchResponse:
    """
    Process an ingestion batch atomically and idempotently.
    Enforces:
    - Replay of identical requests returns stored response.
    - Reused key with different payload returns HTTP 409 Conflict.
    - Record-level deduplication via (source_system, source_message_id).
    - When atomic=True, an invalid record aborts and rolls back newly inserted observations.
    """
    now = datetime.now(timezone.utc)
    request_hash = compute_payload_hash(batch)

    # 1. Lock and check Idempotency Key in PostgreSQL
    existing_key = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.key == idempotency_key)
        .with_for_update()
        .first()
    )

    if existing_key:
        if existing_key.status == "processing":
            raise ConflictException(
                message="An ingestion batch with this idempotency key is currently being processed.",
                code="IDEMPOTENCY_IN_PROGRESS",
                details={"idempotency_key": idempotency_key},
            )

        # Check payload consistency
        if existing_key.request_hash and existing_key.request_hash != request_hash:
            raise ConflictException(
                message="This idempotency key has already been used with a different request payload.",
                code="IDEMPOTENCY_CONFLICT",
                details={"idempotency_key": idempotency_key},
            )

        if existing_key.status == "completed" and existing_key.response_payload:
            # Idempotent replay: return cached response without inserting duplicate rows
            return IngestionBatchResponse(**existing_key.response_payload)

    # 2. Register fresh idempotency key in 'processing' state
    if not existing_key:
        new_key = IdempotencyKey(
            key=idempotency_key,
            status="processing",
            request_hash=request_hash,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db.add(new_key)
        db.flush()

    batch_id = f"batch_{now.strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    inserted_ids: List[int] = []
    duplicate_count = 0
    rejected_count = 0
    errors: List[BatchRecordError] = []

    # Cache existing sensor IDs for fast validation
    valid_sensor_ids = {s[0] for s in db.query(Sensor.sensor_id).all()}

    try:
        # Savepoint for atomic rollback
        nested_sp = db.begin_nested()

        for idx, record in enumerate(batch.records):
            # Foreign key validation for sensor
            if record.sensor_id not in valid_sensor_ids:
                error_msg = f"Sensor with ID {record.sensor_id} does not exist."
                errors.append(BatchRecordError(index=idx, source_message_id=record.source_message_id, error=error_msg))
                rejected_count += 1
                if batch.atomic:
                    nested_sp.rollback()
                    raise ValidationException(
                        message=f"Atomic batch validation failed on record {idx}: {error_msg}",
                        code="ATOMIC_BATCH_VALIDATION_FAILED",
                        details={"errors": [e.model_dump() for e in errors]},
                    )
                continue

            # Check record-level duplication via (source_system, source_message_id)
            is_duplicate = (
                db.query(Observation.observation_id)
                .filter(
                    Observation.source_system == record.source_system,
                    Observation.source_message_id == record.source_message_id,
                )
                .first()
            )

            if is_duplicate:
                duplicate_count += 1
                continue

            # Insert new raw observation
            obs = Observation(
                sensor_id=record.sensor_id,
                event_time=record.event_time,
                received_at=record.received_at or now,
                parameter_code=record.parameter_code,
                raw_value=record.raw_value,
                unit=record.unit,
                source_system=record.source_system,
                source_message_id=record.source_message_id,
                payload_hash=record.payload_hash,
            )
            db.add(obs)
            db.flush()
            inserted_ids.append(obs.observation_id)

        # Commit savepoint
        nested_sp.commit()

        # Build response summary
        response = IngestionBatchResponse(
            batch_id=batch_id,
            status="committed" if rejected_count == 0 else "partial",
            received_count=len(batch.records),
            inserted_count=len(inserted_ids),
            duplicate_count=duplicate_count,
            rejected_count=rejected_count,
            observation_ids=inserted_ids,
            errors=errors,
        )

        # Mark idempotency key as completed and cache response payload
        key_record = db.query(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key).one()
        key_record.status = "completed"
        key_record.response_payload = response.model_dump(mode="json")

        # Record audit event
        log_audit_event(
            db=db,
            entity_type="ingestion_batch",
            entity_id=batch_id,
            action="ingest_batch",
            actor_id=actor_id,
            reason=f"Batch ingestion of {len(batch.records)} records.",
            details={
                "idempotency_key": idempotency_key,
                "inserted_count": len(inserted_ids),
                "duplicate_count": duplicate_count,
                "rejected_count": rejected_count,
            },
        )

        db.commit()
        return response

    except (ValidationException, ConflictException):
        db.rollback()
        # Clean up in-progress idempotency key on explicit validation rollback
        cleanup_db = Session.object_session(existing_key) if existing_key else None
        if not cleanup_db:
            with db.begin():
                db.query(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key).delete()
        raise
    except Exception as e:
        db.rollback()
        # Ensure processing key is removed or marked failed
        try:
            with db.begin():
                db.query(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key).delete()
        except Exception:
            pass
        raise e
