"""Error handling middleware for CloudSound services.

Provides comprehensive exception handling with structured responses,
error codes, and proper logging for debugging and monitoring.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)
import structlog
from typing import Any, Dict, Optional

from ..exceptions import (
    CloudSoundException,
    ErrorCode,
    ValidationError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseIntegrityError,
    DuplicateRecordError,
)

logger = structlog.get_logger(__name__)


def get_correlation_id(request: Request) -> Optional[str]:
    """Extract correlation ID from request state or headers."""
    # Try to get from request state (set by CorrelationIDMiddleware)
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        return correlation_id
    
    # Fallback to header
    return request.headers.get("X-Correlation-ID")


def build_error_response(
    error: str,
    error_code: str,
    status_code: int,
    path: str,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build standardized error response."""
    response = {
        "error": error,
        "error_code": error_code,
        "status_code": status_code,
        "path": path,
    }
    
    if details:
        response["details"] = details
    
    if correlation_id:
        response["correlation_id"] = correlation_id
    
    return response


async def cloudsound_exception_handler(
    request: Request,
    exc: CloudSoundException,
) -> JSONResponse:
    """Handle CloudSound custom exceptions.
    
    Provides structured error responses with error codes for all
    custom exceptions in the CloudSound platform.
    """
    correlation_id = get_correlation_id(request)
    
    logger.warning(
        "cloudsound_exception",
        error_code=exc.error_code.value,
        error=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
        method=request.method,
        details=exc.details,
        correlation_id=correlation_id,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response(
            error=exc.message,
            error_code=exc.error_code.value,
            status_code=exc.status_code,
            path=request.url.path,
            details=exc.details,
            correlation_id=correlation_id,
        ),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle HTTP exceptions with standardized format."""
    correlation_id = get_correlation_id(request)
    
    # Map HTTP status codes to error codes
    error_code_map = {
        400: ErrorCode.BAD_REQUEST,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        409: ErrorCode.CONFLICT,
        422: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.RATE_LIMITED,
        500: ErrorCode.INTERNAL_ERROR,
        502: ErrorCode.EXTERNAL_SERVICE_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
        504: ErrorCode.TIMEOUT,
    }
    
    error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    
    logger.warning(
        "http_exception",
        error_code=error_code.value,
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response(
            error=str(exc.detail) if exc.detail else "HTTP Error",
            error_code=error_code.value,
            status_code=exc.status_code,
            path=request.url.path,
            correlation_id=correlation_id,
        ),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic validation exceptions with detailed error information."""
    correlation_id = get_correlation_id(request)
    
    # Format validation errors for better readability
    formatted_errors = []
    for error in exc.errors():
        formatted_error = {
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", "Invalid value"),
            "type": error.get("type", "unknown"),
        }
        if "input" in error:
            # Only include input for non-sensitive fields
            formatted_error["input"] = error["input"]
        formatted_errors.append(formatted_error)
    
    logger.warning(
        "validation_error",
        error_code=ErrorCode.VALIDATION_ERROR.value,
        errors=formatted_errors,
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=build_error_response(
            error="Request validation failed",
            error_code=ErrorCode.VALIDATION_ERROR.value,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            path=request.url.path,
            details={"validation_errors": formatted_errors},
            correlation_id=correlation_id,
        ),
    )


async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    """Handle SQLAlchemy database exceptions.
    
    Converts database exceptions to appropriate CloudSound exceptions
    with proper error codes and safe error messages.
    """
    correlation_id = get_correlation_id(request)
    
    # Determine specific error type
    if isinstance(exc, IntegrityError):
        # Check for common integrity errors
        error_str = str(exc.orig) if exc.orig else str(exc)
        
        if "unique" in error_str.lower() or "duplicate" in error_str.lower():
            error_code = ErrorCode.DUPLICATE_RECORD
            message = "Record already exists"
            status_code = 409
        elif "foreign key" in error_str.lower():
            error_code = ErrorCode.DATABASE_INTEGRITY_ERROR
            message = "Referenced record does not exist"
            status_code = 409
        else:
            error_code = ErrorCode.DATABASE_INTEGRITY_ERROR
            message = "Database integrity constraint violation"
            status_code = 409
    elif isinstance(exc, OperationalError):
        error_code = ErrorCode.DATABASE_CONNECTION_ERROR
        message = "Database connection error"
        status_code = 503
    else:
        error_code = ErrorCode.DATABASE_ERROR
        message = "Database operation failed"
        status_code = 500
    
    # Log with full error details (but don't expose to client)
    logger.error(
        "database_exception",
        error_code=error_code.value,
        error_type=type(exc).__name__,
        error=str(exc),
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status_code,
        content=build_error_response(
            error=message,
            error_code=error_code.value,
            status_code=status_code,
            path=request.url.path,
            correlation_id=correlation_id,
        ),
    )


async def general_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unhandled exceptions.
    
    Catches all unhandled exceptions and returns a safe error response
    while logging full details for debugging.
    """
    correlation_id = get_correlation_id(request)
    
    # Check if it's a SQLAlchemy exception
    if isinstance(exc, SQLAlchemyError):
        return await sqlalchemy_exception_handler(request, exc)
    
    # Log full error details for debugging
    logger.error(
        "unhandled_exception",
        error_code=ErrorCode.INTERNAL_ERROR.value,
        error_type=type(exc).__name__,
        error=str(exc),
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
        exc_info=True,
    )
    
    # Return safe error message (don't expose internal details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=build_error_response(
            error="An unexpected error occurred",
            error_code=ErrorCode.INTERNAL_ERROR.value,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            path=request.url.path,
            correlation_id=correlation_id,
        ),
    )


def register_exception_handlers(app):
    """Register all exception handlers with a FastAPI app.
    
    Usage:
        from cloudsound_shared.middleware.error_handler import register_exception_handlers
        
        app = FastAPI()
        register_exception_handlers(app)
    """
    from sqlalchemy.exc import SQLAlchemyError
    
    app.add_exception_handler(CloudSoundException, cloudsound_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
