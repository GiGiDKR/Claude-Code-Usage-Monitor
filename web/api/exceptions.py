"""
Exception handlers and error management for the API.

This module provides centralized error handling and validation.
"""

import logging
from datetime import datetime
from typing import Union

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .models.schemas import ErrorResponse

logger = logging.getLogger("api")


class APIException(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        """
        Initialize API exception.

        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Optional error code
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class DataSourceException(APIException):
    """Exception for data source errors."""

    def __init__(self, message: str = "Data source unavailable"):
        super().__init__(message, status_code=503, error_code="DATA_SOURCE_ERROR")


class ValidationException(APIException):
    """Exception for validation errors."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=422, error_code="VALIDATION_ERROR")


class ConfigurationException(APIException):
    """Exception for configuration errors."""

    def __init__(self, message: str = "Configuration error"):
        super().__init__(message, status_code=400, error_code="CONFIG_ERROR")


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Handle custom API exceptions.

    Args:
        request: FastAPI request
        exc: API exception

    Returns:
        JSON error response
    """
    logger.error(
        f"API Exception: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        },
    )

    error_response = ErrorResponse(
        error=exc.message,
        error_code=exc.error_code,
        timestamp=datetime.now(),
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions.

    Args:
        request: FastAPI request
        exc: HTTP exception

    Returns:
        JSON error response
    """
    logger.warning(
        f"HTTP Exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        },
    )

    error_response = ErrorResponse(
        error=str(exc.detail),
        error_code=f"HTTP_{exc.status_code}",
        timestamp=datetime.now(),
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump()
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """
    Handle validation exceptions.

    Args:
        request: FastAPI request
        exc: Validation exception

    Returns:
        JSON error response
    """
    logger.warning(
        f"Validation Error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors() if hasattr(exc, "errors") else None,
        },
    )

    error_details = {
        "path": request.url.path,
        "method": request.method,
    }

    if hasattr(exc, "errors"):
        error_details["validation_errors"] = exc.errors()

    error_response = ErrorResponse(
        error="Validation failed",
        error_code="VALIDATION_ERROR",
        timestamp=datetime.now(),
        details=error_details,
    )

    return JSONResponse(status_code=422, content=error_response.model_dump())


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: FastAPI request
        exc: Exception

    Returns:
        JSON error response
    """
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
        exc_info=True,
    )

    error_response = ErrorResponse(
        error="Internal server error",
        error_code="INTERNAL_ERROR",
        timestamp=datetime.now(),
        details={
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(status_code=500, content=error_response.model_dump())


def register_exception_handlers(app) -> None:
    """
    Register exception handlers with FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


# Utility functions for common validations


def validate_plan_type(plan: str) -> str:
    """
    Validate plan type.

    Args:
        plan: Plan type string

    Returns:
        Validated plan type

    Raises:
        ValidationException: If plan type is invalid
    """
    valid_plans = ["pro", "max5", "max20", "custom_max"]
    if plan not in valid_plans:
        raise ValidationException(
            f"Invalid plan type: {plan}. Must be one of: {', '.join(valid_plans)}"
        )
    return plan


def validate_pagination(page: int, page_size: int) -> tuple[int, int]:
    """
    Validate pagination parameters.

    Args:
        page: Page number
        page_size: Page size

    Returns:
        Validated (page, page_size) tuple

    Raises:
        ValidationException: If parameters are invalid
    """
    if page < 1:
        raise ValidationException("Page number must be >= 1")

    if page_size < 1 or page_size > 1000:
        raise ValidationException("Page size must be between 1 and 1000")

    return page, page_size


def validate_date_range(start_date, end_date) -> tuple:
    """
    Validate date range.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        Validated date range

    Raises:
        ValidationException: If date range is invalid
    """
    if start_date and end_date and start_date > end_date:
        raise ValidationException("Start date must be before end date")

    return start_date, end_date
