from typing import Optional, List, Callable
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.user import UserAccount
from backend.app.core.security import decode_access_token
from backend.app.core.errors import UnauthorizedException, ForbiddenException

ROLE_HIERARCHY = {
    "admin": {"admin", "steward", "reviewer", "researcher"},
    "steward": {"steward", "reviewer", "researcher"},
    "reviewer": {"reviewer", "researcher"},
    "researcher": {"researcher"},
}


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> UserAccount:
    """Extract and authenticate user from Authorization: Bearer <JWT> header."""
    if not authorization:
        raise UnauthorizedException(
            message="Missing Authorization header.",
            code="MISSING_AUTHORIZATION_HEADER",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException(
            message="Invalid Authorization header format. Expected 'Bearer <token>'.",
            code="INVALID_AUTHORIZATION_FORMAT",
        )

    token = parts[1]
    try:
        payload = decode_access_token(token)
    except Exception as e:
        raise UnauthorizedException(
            message=f"Invalid or expired token: {str(e)}",
            code="INVALID_TOKEN",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(message="Token missing subject claim.", code="MALFORMED_TOKEN")

    user = db.query(UserAccount).filter(UserAccount.user_id == int(user_id)).first()
    if not user or not user.is_active:
        raise UnauthorizedException(message="User account inactive or not found.", code="USER_INACTIVE")

    return user


def require_role(*required_roles: str) -> Callable[[UserAccount], UserAccount]:
    """Dependency enforcing role-based access control based on user hierarchy."""
    def role_checker(current_user: UserAccount = Depends(get_current_user)) -> UserAccount:
        user_role = current_user.role
        granted_roles = ROLE_HIERARCHY.get(user_role, set())

        # Check if user has any of the required permissions
        if not any(req in granted_roles for req in required_roles):
            raise ForbiddenException(
                message=f"User role '{user_role}' lacks permission for this action. Required: {list(required_roles)}.",
                code="FORBIDDEN_INSUFFICIENT_ROLE",
                details={"user_role": user_role, "required_roles": list(required_roles)},
            )
        return current_user

    return role_checker
