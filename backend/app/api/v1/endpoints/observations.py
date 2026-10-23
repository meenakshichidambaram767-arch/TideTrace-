from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.db.session import get_db
from backend.app.models.telemetry import Observation
from backend.app.models.quality import QualityTestResult
from backend.app.models.revision import ObservationRevision
from backend.app.models.user import UserAccount
from backend.app.schemas.revision import ObservationSummary, ObservationDetailResponse, RevisionResponse
from backend.app.schemas.quality import QualityTestResultItem
from backend.app.schemas.common import PaginatedResponse
from backend.app.api.v1.dependencies.auth import get_current_user
from backend.app.core.errors import NotFoundException

router = APIRouter(prefix="/observations", tags=["Observations"])


@router.get("", response_model=PaginatedResponse[ObservationSummary], status_code=status.HTTP_200_OK)
def search_observations(
    sensor_id: Optional[int] = Query(None),
    parameter_code: Optional[str] = Query(None),
    from_time: Optional[datetime] = Query(None),
    to_time: Optional[datetime] = Query(None),
    quality_flag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search observations with multi-dimensional filtering and pagination."""
    query = db.query(Observation)
    if sensor_id is not None:
        query = query.filter(Observation.sensor_id == sensor_id)
    if parameter_code is not None:
        query = query.filter(Observation.parameter_code == parameter_code)
    if from_time is not None:
        query = query.filter(Observation.event_time >= from_time)
    if to_time is not None:
        query = query.filter(Observation.event_time <= to_time)

    total = query.count()
    records = (
        query.order_by(desc(Observation.event_time))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for r in records:
        latest_rev = (
            db.query(ObservationRevision)
            .filter(ObservationRevision.observation_id == r.observation_id)
            .order_by(desc(ObservationRevision.revision_number))
            .first()
        )
        latest_test = (
            db.query(QualityTestResult)
            .filter(QualityTestResult.observation_id == r.observation_id)
            .order_by(desc(QualityTestResult.tested_at))
            .first()
        )
        rev_count = (
            db.query(ObservationRevision)
            .filter(ObservationRevision.observation_id == r.observation_id)
            .count()
        )

        items.append(
            ObservationSummary(
                observation_id=r.observation_id,
                sensor_id=r.sensor_id,
                event_time=r.event_time,
                received_at=r.received_at,
                parameter_code=r.parameter_code,
                raw_value=r.raw_value,
                unit=r.unit,
                source_system=r.source_system,
                source_message_id=r.source_message_id,
                latest_quality_flag=latest_test.flag if latest_test else None,
                current_accepted_value=latest_rev.accepted_value if latest_rev else None,
                current_decision=latest_rev.decision if latest_rev else None,
                revision_count=rev_count,
            )
        )

    return PaginatedResponse(items=items, page=page, page_size=page_size, total=total)


@router.get("/{observation_id}", response_model=ObservationDetailResponse, status_code=status.HTTP_200_OK)
def get_observation_detail(
    observation_id: int = Path(..., ge=1),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full observation detail including raw telemetry, latest flags, and complete revision history."""
    obs = db.query(Observation).filter(Observation.observation_id == observation_id).first()
    if not obs:
        raise NotFoundException(
            message=f"Observation with ID {observation_id} not found.",
            code="OBSERVATION_NOT_FOUND",
            details={"observation_id": observation_id},
        )

    # Revisions
    revisions = (
        db.query(ObservationRevision)
        .filter(ObservationRevision.observation_id == observation_id)
        .order_by(ObservationRevision.revision_number.asc())
        .all()
    )
    latest_rev = revisions[-1] if revisions else None

    # Quality test results
    tests = (
        db.query(QualityTestResult)
        .filter(QualityTestResult.observation_id == observation_id)
        .order_by(desc(QualityTestResult.tested_at))
        .all()
    )
    latest_flag = tests[0].flag if tests else None

    quality_items = [
        QualityTestResultItem(
            test_result_id=t.test_result_id,
            rule_id=t.rule_id,
            rule_name=t.rule.name if t.rule else "unknown",
            rule_version=t.rule.rule_version if t.rule else "v1.0",
            flag=t.flag,
            details=t.details,
            tested_at=t.tested_at,
        )
        for t in tests
    ]

    rev_items = [
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

    return ObservationDetailResponse(
        observation_id=obs.observation_id,
        sensor_id=obs.sensor_id,
        event_time=obs.event_time,
        received_at=obs.received_at,
        parameter_code=obs.parameter_code,
        raw_value=obs.raw_value,
        unit=obs.unit,
        source_system=obs.source_system,
        source_message_id=obs.source_message_id,
        payload_hash=obs.payload_hash,
        current_accepted_value=latest_rev.accepted_value if latest_rev else None,
        current_decision=latest_rev.decision if latest_rev else None,
        latest_quality_flag=latest_flag,
        quality_test_count=len(tests),
        revision_count=len(revisions),
        quality_results=quality_items,
        revisions=rev_items,
    )
