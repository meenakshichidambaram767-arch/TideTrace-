from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.db.session import get_db

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    """Public health check confirming API operational status and PostgreSQL connectivity."""
    db.execute(text("SELECT 1")).scalar()
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
