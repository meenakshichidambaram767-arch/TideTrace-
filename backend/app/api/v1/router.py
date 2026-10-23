from fastapi import APIRouter

from backend.app.api.v1.endpoints import (
    auth,
    health,
    ingestion,
    quality,
    revisions,
    observations,
    analyses,
    audit,
    database_stats,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(ingestion.router)
api_router.include_router(quality.router)
api_router.include_router(revisions.router)
api_router.include_router(observations.router)
api_router.include_router(analyses.router)
api_router.include_router(audit.router)
api_router.include_router(database_stats.router)

