from typing import List
from fastapi import APIRouter, Depends, Header, Path, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.revision import RevisionCreate, RevisionResponse
from backend.app.models.user import UserAccount
from backend.app.api.v1.dependencies.auth import get_current_user, require_role
from backend.app.services.revision_service import append_observation_revision, list_observation_revisions

router = APIRouter(tags=["Observation Revisions"])


@router.get(
    "/observations/{observation_id}/revisions",
    response_model=List[RevisionResponse],
    status_code=status.HTTP_200_OK,
)
def get_observation_revision_history(
    observation_id: int = Path(..., ge=1),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the full append-only revision history for an observation in chronological order."""
    return list_observation_revisions(db=db, observation_id=observation_id)


@router.post(
    "/observations/{observation_id}/revisions",
    response_model=RevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_observation_revision_endpoint(
    payload: RevisionCreate,
    observation_id: int = Path(..., ge=1),
    if_match_revision: int = Header(..., alias="If-Match-Revision", ge=0),
    current_user: UserAccount = Depends(require_role("reviewer")),
    db: Session = Depends(get_db),
):
    """
    Append an immutable, reviewed measurement revision.
    
    Guarantees:
    - Reviewer ID is derived from authenticated user token, never client payload.
    - SELECT ... FOR UPDATE serializes concurrent submissions.
    - If-Match-Revision precondition check returns 409 Conflict if outdated.
    - Reason must be >= 5 characters.
    - Raw observation and prior revisions remain unchanged.
    """
    return append_observation_revision(
        db=db,
        observation_id=observation_id,
        expected_revision=if_match_revision,
        revision_in=payload,
        reviewer_id=current_user.user_id,
    )
