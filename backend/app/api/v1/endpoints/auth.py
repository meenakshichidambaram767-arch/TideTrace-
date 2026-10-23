from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.user import UserAccount
from backend.app.schemas.auth import TokenRequest, TokenResponse, UserProfile
from backend.app.core.security import verify_password, create_access_token
from backend.app.core.errors import UnauthorizedException

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login_for_access_token(
    payload: TokenRequest,
    db: Session = Depends(get_db),
):
    """Authenticate with username and password to receive a JWT Bearer token."""
    user = db.query(UserAccount).filter(UserAccount.username == payload.username).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedException(
            message="Invalid username or password.",
            code="INVALID_CREDENTIALS",
        )

    token_data = {
        "sub": str(user.user_id),
        "username": user.username,
        "name": user.full_name,
        "role": user.role,
    }
    access_token = create_access_token(data=token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserProfile(
            user_id=user.user_id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
        ),
    )
