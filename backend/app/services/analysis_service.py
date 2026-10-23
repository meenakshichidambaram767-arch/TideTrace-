import statistics
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc, text

from backend.app.models.telemetry import Observation
from backend.app.models.revision import ObservationRevision
from backend.app.models.analysis import AnalysisRun, AnalysisInput, AnalysisResult
from backend.app.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    AnalysisDetailResponse,
    AnalysisResultItem,
    ManifestItem,
    ReplayResponse,
)
from backend.app.schemas.common import PaginatedResponse
from backend.app.core.errors import NotFoundException, ValidationException
from backend.app.services.audit_service import log_audit_event


UNSUPPORTED_VERSIONS = {"unsupported", "deprecated", "legacy-incompatible", "incompatible-v0"}


def is_version_supported(query_version: str) -> bool:
    """Validate whether an analysis calculation kernel version is supported."""
    if not query_version or query_version.lower() in UNSUPPORTED_VERSIONS:
        return False
    return True


def compute_metric_value(values: List[float], metric: str) -> float:
    """Compute mathematical metric across resolved values."""
    if not values:
        return 0.0

    if metric == "count":
        return float(len(values))
    elif metric == "mean":
        return sum(values) / len(values)
    elif metric == "min":
        return min(values)
    elif metric == "max":
        return max(values)
    elif metric == "median":
        return statistics.median(values)
    elif metric == "standard_deviation":
        if len(values) < 2:
            return 0.0
        return statistics.pstdev(values)
    else:
        raise ValidationException(f"Unsupported metric: '{metric}'", code="INVALID_METRIC")


def execute_analysis(
    db: Session,
    analysis_in: AnalysisCreate,
    creator_id: int,
) -> AnalysisResponse:
    """
    Execute reproducible analysis, freezing the exact input observation and revision IDs.
    
    Guarantees:
    - Filters observations deterministically.
    - Resolves accepted revision at execution time, or raw telemetry based on revision_policy.
    - Captures frozen input manifest into analysis_input.
    - Stores calculated results in analysis_result.
    - Logs audit trail.
    """
    now = datetime.now(timezone.utc)

    # 1. Validate calculation version
    if not is_version_supported(analysis_in.query_version):
        raise ValidationException(
            message=f"Query version '{analysis_in.query_version}' is not supported by the calculation engine.",
            code="QUERY_VERSION_UNSUPPORTED",
            details={"query_version": analysis_in.query_version},
        )

    # 2. Filter observations using parameterized query
    filters = analysis_in.filters
    obs_query = db.query(Observation).filter(Observation.parameter_code == filters.parameter_code)

    if filters.sensor_ids:
        obs_query = obs_query.filter(Observation.sensor_id.in_(filters.sensor_ids))
    if filters.from_time:
        obs_query = obs_query.filter(Observation.event_time >= filters.from_time)
    if filters.to_time:
        obs_query = obs_query.filter(Observation.event_time <= filters.to_time)

    observations = obs_query.order_by(Observation.event_time.asc()).all()

    # 3. Resolve exact measurement values and manifest inputs
    resolved_values: List[float] = []
    manifest_records: List[Dict[str, Any]] = []
    unit = observations[0].unit if observations else "unit"

    for obs in observations:
        if filters.revision_policy == "latest_accepted_at_run":
            # Lookup latest accepted or corrected revision created at or before run time
            latest_rev = (
                db.query(ObservationRevision)
                .filter(
                    ObservationRevision.observation_id == obs.observation_id,
                    ObservationRevision.decision.in_(["accepted", "corrected"]),
                    ObservationRevision.created_at <= now,
                )
                .order_by(desc(ObservationRevision.revision_number))
                .first()
            )
            if latest_rev:
                resolved_values.append(float(latest_rev.accepted_value))
                manifest_records.append({
                    "observation_id": obs.observation_id,
                    "revision_id": latest_rev.revision_id,
                    "input_role": "revision",
                })
            else:
                resolved_values.append(float(obs.raw_value))
                manifest_records.append({
                    "observation_id": obs.observation_id,
                    "revision_id": None,
                    "input_role": "raw",
                })
        else:
            # Raw only policy
            resolved_values.append(float(obs.raw_value))
            manifest_records.append({
                "observation_id": obs.observation_id,
                "revision_id": None,
                "input_role": "raw",
            })

    # 4. Compute metric
    computed_val = compute_metric_value(resolved_values, analysis_in.metric)

    # 5. Persist AnalysisRun
    new_run = AnalysisRun(
        analysis_name=analysis_in.analysis_name,
        metric=analysis_in.metric,
        query_version=analysis_in.query_version,
        filters=analysis_in.filters.model_dump(mode="json"),
        parameters=analysis_in.parameters,
        status="completed",
        creator_id=creator_id,
        created_at=now,
    )
    db.add(new_run)
    db.flush()

    # 6. Freeze input manifest
    if analysis_in.save_input_manifest and manifest_records:
        inputs_to_insert = [
            AnalysisInput(
                analysis_id=new_run.analysis_id,
                observation_id=m["observation_id"],
                revision_id=m["revision_id"],
                input_role=m["input_role"],
            )
            for m in manifest_records
        ]
        db.bulk_save_objects(inputs_to_insert)

    # 7. Persist result
    result_record = AnalysisResult(
        analysis_id=new_run.analysis_id,
        metric_name=f"{analysis_in.metric}_{filters.parameter_code}",
        metric_value=Decimal(str(round(computed_val, 6))),
        unit=unit,
        computed_at=now,
    )
    db.add(result_record)
    db.flush()

    # 8. Record audit event
    log_audit_event(
        db=db,
        entity_type="analysis_run",
        entity_id=str(new_run.analysis_id),
        action="create_analysis",
        actor_id=creator_id,
        reason=f"Executed analysis '{new_run.analysis_name}' (Metric: {new_run.metric}).",
        details={
            "query_version": new_run.query_version,
            "input_count": len(resolved_values),
            "metric_value": computed_val,
        },
    )

    db.commit()

    return AnalysisResponse(
        analysis_id=new_run.analysis_id,
        analysis_name=new_run.analysis_name,
        metric=new_run.metric,
        status=new_run.status,
        created_at=new_run.created_at,
        query_version=new_run.query_version,
        input_count=len(resolved_values),
        results=[
            AnalysisResultItem(
                metric_name=result_record.metric_name,
                metric_value=result_record.metric_value,
                unit=result_record.unit,
            )
        ],
    )


def get_analysis_detail(db: Session, analysis_id: int) -> AnalysisDetailResponse:
    """Retrieve full analysis details including frozen manifest and results."""
    run = db.query(AnalysisRun).filter(AnalysisRun.analysis_id == analysis_id).first()
    if not run:
        raise NotFoundException(
            message=f"Analysis with ID {analysis_id} not found.",
            code="ANALYSIS_NOT_FOUND",
            details={"analysis_id": analysis_id},
        )

    results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.analysis_id == analysis_id)
        .all()
    )

    manifest_entries = (
        db.query(AnalysisInput)
        .filter(AnalysisInput.analysis_id == analysis_id)
        .all()
    )

    return AnalysisDetailResponse(
        analysis_id=run.analysis_id,
        analysis_name=run.analysis_name,
        metric=run.metric,
        query_version=run.query_version,
        filters=run.filters,
        parameters=run.parameters,
        status=run.status,
        creator_id=run.creator_id,
        created_at=run.created_at,
        input_count=len(manifest_entries),
        results=[
            AnalysisResultItem(
                metric_name=r.metric_name,
                metric_value=r.metric_value,
                unit=r.unit,
            )
            for r in results
        ],
        manifest=[
            ManifestItem(
                observation_id=m.observation_id,
                revision_id=m.revision_id,
                input_role=m.input_role,
            )
            for m in manifest_entries
        ],
    )


def list_analyses(
    db: Session,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[AnalysisResponse]:
    """List executed analysis runs."""
    query = db.query(AnalysisRun)
    total = query.count()
    runs = (
        query.order_by(desc(AnalysisRun.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for run in runs:
        results = db.query(AnalysisResult).filter(AnalysisResult.analysis_id == run.analysis_id).all()
        input_count = db.query(AnalysisInput).filter(AnalysisInput.analysis_id == run.analysis_id).count()
        items.append(
            AnalysisResponse(
                analysis_id=run.analysis_id,
                analysis_name=run.analysis_name,
                metric=run.metric,
                status=run.status,
                created_at=run.created_at,
                query_version=run.query_version,
                input_count=input_count,
                results=[
                    AnalysisResultItem(
                        metric_name=r.metric_name,
                        metric_value=r.metric_value,
                        unit=r.unit,
                    )
                    for r in results
                ],
            )
        )

    return PaginatedResponse(items=items, page=page, page_size=page_size, total=total)


def replay_analysis(
    db: Session,
    analysis_id: int,
    actor_id: Optional[int] = None,
) -> ReplayResponse:
    """
    Replay an analysis strictly from its frozen input manifest.
    
    Guarantees:
    - Never queries the latest observations dynamically.
    - Reads the exact historical revision specified in the manifest, ignoring subsequent revisions.
    - Validates query_version support; returns clear error if unsupported.
    - Distinguishes manifest integrity verification from output equality.
    - Persists audit event.
    """
    now = datetime.now(timezone.utc)

    # 1. Fetch analysis run
    run = db.query(AnalysisRun).filter(AnalysisRun.analysis_id == analysis_id).first()
    if not run:
        raise NotFoundException(
            message=f"Analysis with ID {analysis_id} not found.",
            code="ANALYSIS_NOT_FOUND",
            details={"analysis_id": analysis_id},
        )

    # 2. Check calculation version availability
    if not is_version_supported(run.query_version):
        raise ValidationException(
            message=f"Analysis query version '{run.query_version}' is no longer supported for replay.",
            code="REPLAY_VERSION_UNSUPPORTED",
            details={"analysis_id": analysis_id, "query_version": run.query_version},
        )

    # 3. Read frozen manifest
    manifest_entries = (
        db.query(AnalysisInput)
        .filter(AnalysisInput.analysis_id == analysis_id)
        .all()
    )

    # 4. Verify manifest integrity: all referenced observations must exist
    manifest_verified = True
    if not manifest_entries:
        manifest_verified = False

    replayed_values: List[float] = []

    for entry in manifest_entries:
        if entry.revision_id is not None:
            # Query specific revision recorded in manifest
            rev = (
                db.query(ObservationRevision.accepted_value)
                .filter(ObservationRevision.revision_id == entry.revision_id)
                .first()
            )
            if rev:
                replayed_values.append(float(rev[0]))
            else:
                manifest_verified = False
        else:
            # Query raw observation recorded in manifest
            raw_obs = (
                db.query(Observation.raw_value)
                .filter(Observation.observation_id == entry.observation_id)
                .first()
            )
            if raw_obs:
                replayed_values.append(float(raw_obs[0]))
            else:
                manifest_verified = False

    # 5. Recompute metric
    replayed_val = compute_metric_value(replayed_values, run.metric)

    # 6. Fetch original results
    original_results = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.analysis_id == analysis_id)
        .all()
    )

    orig_items = [
        AnalysisResultItem(
            metric_name=r.metric_name,
            metric_value=r.metric_value,
            unit=r.unit,
        )
        for r in original_results
    ]

    unit = orig_items[0].unit if orig_items else "unit"
    metric_name = orig_items[0].metric_name if orig_items else f"{run.metric}_result"

    replayed_items = [
        AnalysisResultItem(
            metric_name=metric_name,
            metric_value=Decimal(str(round(replayed_val, 6))),
            unit=unit,
        )
    ]

    # 7. Compare results with tolerance 1e-5
    results_match = False
    if orig_items:
        orig_val = float(orig_items[0].metric_value)
        results_match = abs(orig_val - replayed_val) < 1e-5

    matches = results_match and manifest_verified

    # 8. Log audit event
    log_audit_event(
        db=db,
        entity_type="analysis_run",
        entity_id=str(analysis_id),
        action="replay_analysis",
        actor_id=actor_id,
        reason=f"Replayed analysis #{analysis_id} (Matches: {matches}, ManifestVerified: {manifest_verified}).",
        details={
            "query_version": run.query_version,
            "manifest_verified": manifest_verified,
            "matches": matches,
            "replayed_metric_value": replayed_val,
        },
    )

    db.commit()

    return ReplayResponse(
        analysis_id=run.analysis_id,
        replayed_at=now,
        original_results=orig_items,
        replayed_results=replayed_items,
        matches=matches,
        input_manifest_verified=manifest_verified,
    )
