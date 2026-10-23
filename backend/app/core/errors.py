from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ConflictException(AppException):
    def __init__(self, message: str, code: str = "CONFLICT", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=status.HTTP_409_CONFLICT, details=details)


class NotFoundException(AppException):
    def __init__(self, message: str, code: str = "NOT_FOUND", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=status.HTTP_404_NOT_FOUND, details=details)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required.", code: str = "UNAUTHORIZED", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Permission denied.", code: str = "FORBIDDEN", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=status.HTTP_403_FORBIDDEN, details=details)


class ValidationException(AppException):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", details: Optional[Any] = None):
        super().__init__(code=code, message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)


def format_error_response(request: Request, code: str, message: str, details: Optional[Any] = None, status_code: int = 400) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "req_unknown")
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id,
            }
        },
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return format_error_response(
        request=request,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return format_error_response(
        request=request,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details=exc.errors(),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Do not leak internal stack traces
    return format_error_response(
        request=request,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred.",
        details=str(exc) if request.app.debug else None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
