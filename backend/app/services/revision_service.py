from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.telemetry import Observation
from backend.app.models.revision import ObservationRevision
from backend.app.schemas.revision import RevisionCreate, RevisionResponse
from backend.app.core.errors import ConflictException, NotFoundException, ValidationException
from backend.app.services.audit_service import log_audit_event


def append_observation_revision(
    db: Session,
    observation_id: int,
    expected_revision: int,
    revision_in: RevisionCreate,
    reviewer_id: int,
) -> RevisionResponse:
    """
    Append an immutable, curated measurement revision with pessimistic concurrency locking.
    
    Guarantees:
    1. Locks the target observation row with SELECT ... FOR UPDATE.
    2. Verifies the If-Match-Revision precondition against the current revision number.
    3. Allocates sequential revision_number in the locked transaction.
    4. Enforces reason length >= 5 characters.
    5. Returns HTTP 409 Conflict if expected_revision does not match current state.
    6. Logs an immutable audit event for the action.
    7. Raw observation is 100% preserved.
    """
    now = datetime.now(timezone.utc)

    # 1. Enforce minimum reason length
    if len(revision_in.reason.strip()) < 5:
        raise ValidationException(
            message="Revision reason must be at least 5 characters long.",
            code="INVALID_REVISION_REASON",
            details={"min_length": 5, "provided_length": len(revision_in.reason.strip())},
        )

    # 2. Acquire row-level lock on the target observation
    obs = (
        db.query(Observation)
        .filter(Observation.observation_id == observation_id)
        .with_for_update()
        .first()
    )

    if not obs:
        raise NotFoundException(
            message=f"Observation with ID {observation_id} not found.",
            code="OBSERVATION_NOT_FOUND",
            details={"observation_id": observation_id},
        )

    # 3. Retrieve current maximum revision number for this observation
    current_max_rev = (
        db.query(func.coalesce(func.max(ObservationRevision.revision_number), 0))
        .filter(ObservationRevision.observation_id == observation_id)
        .scalar()
    )

    # 4. Check optimistic precondition (If-Match-Revision)
    # If no revisions exist yet, expected_revision must be 0 (or match whatever base the client holds)
    if current_max_rev != expected_revision:
        raise ConflictException(
            message="The observation has a newer revision or the expected revision precondition does not match.",
            code="REVISION_CONFLICT",
            details={
                "expected_revision": expected_revision,
                "current_revision": current_max_rev,
                "observation_id": observation_id,
            },
        )

    # 5. Allocate next revision number
    next_revision_number = current_max_rev + 1

    # 6. Insert new immutable revision record
    new_rev = ObservationRevision(
        observation_id=obs.observation_id,
        revision_number=next_revision_number,
        accepted_value=revision_in.accepted_value,
        decision=revision_in.decision,
        reason=revision_in.reason.strip(),
        reviewer_id=reviewer_id,
        calibration_id=revision_in.calibration_id,
        created_at=now,
    )
    db.add(new_rev)
    db.flush()

    # 7. Record audit event
    log_audit_event(
        db=db,
        entity_type="observation",
        entity_id=str(obs.observation_id),
        action="append_revision",
        actor_id=reviewer_id,
        reason=revision_in.reason.strip(),
        details={
            "revision_number": next_revision_number,
            "decision": revision_in.decision,
            "accepted_value": float(revision_in.accepted_value),
            "calibration_id": revision_in.calibration_id,
        },
    )

    db.commit()

    return RevisionResponse(
        revision_id=new_rev.revision_id,
        observation_id=new_rev.observation_id,
        revision_number=new_rev.revision_number,
        accepted_value=new_rev.accepted_value,
        decision=new_rev.decision,
        reason=new_rev.reason,
        reviewer_id=new_rev.reviewer_id,
        calibration_id=new_rev.calibration_id,
        created_at=new_rev.created_at,
    )


def list_observation_revisions(db: Session, observation_id: int) -> List[RevisionResponse]:
    """Retrieve full append-only revision history for an observation in chronological order."""
    obs = db.query(Observation.observation_id).filter(Observation.observation_id == observation_id).first()
    if not obs:
        raise NotFoundException(
            message=f"Observation with ID {observation_id} not found.",
            code="OBSERVATION_NOT_FOUND",
            details={"observation_id": observation_id},
        )

    revisions = (
        db.query(ObservationRevision)
        .filter(ObservationRevision.observation_id == observation_id)
        .order_by(ObservationRevision.revision_number.asc())
        .all()
    )

    return [
        RevisionResponse(
            revision_id=r.revision_id,
            observation_id=r.observation_id,
            revision_number=r.revision_number,
            accepted_value=r.accepted_value,
            decision=r.decision,
            reason=r.reason,
            reviewer_id=r.reviewer_id,
            calibration_id=r.calibration_id,
            created_at=r.created_at,
        )
        for r in revisions
    ]
