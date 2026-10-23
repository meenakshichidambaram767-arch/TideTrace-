from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.quality import QualityRule
from backend.app.models.user import UserAccount
from backend.app.schemas.quality import (
    QualityRuleCreate,
    QualityRuleResponse,
    QualityTestRequest,
    QualityTestResponse,
)
from backend.app.schemas.common import PaginatedResponse
from backend.app.api.v1.dependencies.auth import get_current_user, require_role
from backend.app.services.quality_engine import evaluate_observation_quality
from backend.app.core.errors import ConflictException

router = APIRouter(tags=["Quality Control"])


@router.get("/quality-rules", response_model=PaginatedResponse[QualityRuleResponse], status_code=status.HTTP_200_OK)
def list_quality_rules(
    parameter_code: Optional[str] = Query(None),
    rule_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List quality control rules and versions."""
    query = db.query(QualityRule)
    if parameter_code:
        query = query.filter(QualityRule.parameter_code == parameter_code)
    if rule_type:
        query = query.filter(QualityRule.rule_type == rule_type)
    if is_active is not None:
        query = query.filter(QualityRule.is_active == is_active)

    total = query.count()
    rules = (
        query.order_by(QualityRule.name.asc(), QualityRule.rule_version.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        QualityRuleResponse(
            rule_id=r.rule_id,
            name=r.name,
            parameter_code=r.parameter_code,
            rule_type=r.rule_type,
            thresholds=r.thresholds,
            rule_version=r.rule_version,
            is_active=r.is_active,
            created_at=r.created_at,
        )
        for r in rules
    ]

    return PaginatedResponse(items=items, page=page, page_size=page_size, total=total)


@router.post("/quality-rules", response_model=QualityRuleResponse, status_code=status.HTTP_201_CREATED)
def create_quality_rule_version(
    payload: QualityRuleCreate,
    current_user: UserAccount = Depends(require_role("steward")),
    db: Session = Depends(get_db),
):
    """Create a new immutable quality rule version."""
    existing = (
        db.query(QualityRule)
        .filter(QualityRule.name == payload.name, QualityRule.rule_version == payload.rule_version)
        .first()
    )
    if existing:
        raise ConflictException(
            message=f"A rule version '{payload.rule_version}' for '{payload.name}' already exists. Rule versions are immutable.",
            code="RULE_VERSION_EXISTS",
            details={"name": payload.name, "rule_version": payload.rule_version},
        )

    now = datetime.now(timezone.utc)
    new_rule = QualityRule(
        name=payload.name,
        parameter_code=payload.parameter_code,
        rule_type=payload.rule_type,
        thresholds=payload.thresholds,
        rule_version=payload.rule_version,
        is_active=payload.is_active,
        created_at=now,
    )
    db.add(new_rule)
    db.commit()

    return QualityRuleResponse(
        rule_id=new_rule.rule_id,
        name=new_rule.name,
        parameter_code=new_rule.parameter_code,
        rule_type=new_rule.rule_type,
        thresholds=new_rule.thresholds,
        rule_version=new_rule.rule_version,
        is_active=new_rule.is_active,
        created_at=new_rule.created_at,
    )


@router.post(
    "/observations/{observation_id}/quality-tests",
    response_model=QualityTestResponse,
    status_code=status.HTTP_200_OK,
)
def run_quality_tests_endpoint(
    observation_id: int = Path(..., ge=1),
    payload: Optional[QualityTestRequest] = None,
    current_user: UserAccount = Depends(require_role("reviewer")),
    db: Session = Depends(get_db),
):
    """
    Execute versioned quality tests against an observation.
    Records test outcomes referencing exact rule version used.
    Does not delete or alter raw telemetry.
    """
    req_body = payload or QualityTestRequest()
    return evaluate_observation_quality(
        db=db,
        observation_id=observation_id,
        rule_ids=req_body.rule_ids,
        include_temporal_checks=req_body.include_temporal_checks,
    )
