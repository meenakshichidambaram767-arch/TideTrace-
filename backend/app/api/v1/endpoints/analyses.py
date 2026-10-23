from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.user import UserAccount
from backend.app.schemas.analysis import (
    AnalysisCreate,
    AnalysisResponse,
    AnalysisDetailResponse,
    ReplayResponse,
)
from backend.app.schemas.common import PaginatedResponse
from backend.app.api.v1.dependencies.auth import get_current_user, require_role
from backend.app.services.analysis_service import (
    execute_analysis,
    get_analysis_detail,
    list_analyses,
    replay_analysis,
)

router = APIRouter(prefix="/analyses", tags=["Reproducible Analyses"])


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_analysis_endpoint(
    payload: AnalysisCreate,
    current_user: UserAccount = Depends(require_role("researcher")),
    db: Session = Depends(get_db),
):
    """
    Execute a reproducible analysis, computing metric aggregations and freezing the exact input manifest.
    """
    return execute_analysis(db=db, analysis_in=payload, creator_id=current_user.user_id)


@router.get("", response_model=PaginatedResponse[AnalysisResponse], status_code=status.HTTP_200_OK)
def list_analyses_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List executed analysis snapshots with pagination."""
    return list_analyses(db=db, page=page, page_size=page_size)


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse, status_code=status.HTTP_200_OK)
def get_analysis_detail_endpoint(
    analysis_id: int = Path(..., ge=1),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full analysis details including parameters, results, and frozen input manifest."""
    return get_analysis_detail(db=db, analysis_id=analysis_id)


@router.post("/{analysis_id}/replay", response_model=ReplayResponse, status_code=status.HTTP_200_OK)
def replay_analysis_endpoint(
    analysis_id: int = Path(..., ge=1),
    current_user: UserAccount = Depends(require_role("researcher")),
    db: Session = Depends(get_db),
):
    """
    Replay an analysis strictly from its frozen input manifest.
    Compares recomputed output against original results without querying current dynamic state.
    """
    return replay_analysis(db=db, analysis_id=analysis_id, actor_id=current_user.user_id)
