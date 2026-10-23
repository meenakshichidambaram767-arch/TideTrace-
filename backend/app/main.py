from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.middleware import RequestIdMiddleware
from backend.app.core.errors import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from backend.app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="REST API for ocean sensor ingestion, quality checks, append-only revisions and reproducible analyses.",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)

# CORS Middleware for React UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID Tracing Middleware
app.add_middleware(RequestIdMiddleware)

# Custom Exception Handlers adhering to TideTrace Error Envelope
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
