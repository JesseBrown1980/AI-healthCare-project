"""
Standardized error response formatting utilities.

Provides consistent error response structure across all endpoints.
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import uuid


def create_error_response(
    message: str,
    status_code: int = 500,
    correlation_id: Optional[str] = None,
    error_type: Optional[str] = None,
    hint: Optional[str] = None,
    detail: Optional[str] = None,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.
    
    Args:
        message: Human-readable error message
        status_code: HTTP status code
        correlation_id: Request correlation ID for tracing
        error_type: Type/category of error (e.g., "ValidationError", "ServiceUnavailable")
        hint: Helpful hint for resolving the error
        detail: Additional error details (only in debug mode)
        path: Request path where error occurred
        
    Returns:
        Standardized error response dictionary
    """
    response: Dict[str, Any] = {
        "status": "error",
        "message": message,
        "correlation_id": correlation_id or uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status_code": status_code,
    }
    
    if error_type:
        response["error_type"] = error_type
    
    if hint:
        response["hint"] = hint
    
    if detail:
        response["detail"] = detail
    
    if path:
        response["path"] = path
    
    return response


def get_hint_for_status_code(status_code: int) -> Optional[str]:
    """
    Get a helpful hint message for a given HTTP status code.
    
    Args:
        status_code: HTTP status code
        
    Returns:
        Hint message or None
    """
    hints = {
        400: "Bad request. Please check your input parameters.",
        401: "Please authenticate and try again. Check your access token.",
        403: "You don't have permission to access this resource. Check your roles and scopes.",
        404: "The requested resource was not found. Check the URL and resource ID.",
        409: "Resource conflict. The resource may already exist or be in use.",
        422: "Request validation failed. Check your input parameters.",
        429: "Rate limit exceeded. Please try again later.",
        500: "Internal server error. Please try again later or contact support.",
        503: "Service temporarily unavailable. Please try again in a moment.",
    }
    
    return hints.get(status_code)


def create_http_exception(
    message: str,
    status_code: int = 500,
    error_type: Optional[str] = None,
    hint: Optional[str] = None,
) -> HTTPException:
    """
    Create a standardized HTTPException with hint.
    
    Args:
        message: Error message
        status_code: HTTP status code
        error_type: Type of error
        hint: Helpful hint (auto-generated if not provided)
        
    Returns:
        HTTPException with standardized detail
    """
    if hint is None:
        hint = get_hint_for_status_code(status_code)
    
    detail = message
    if hint:
        detail = f"{message} ({hint})"
    
    return HTTPException(status_code=status_code, detail=detail)


def get_correlation_id(request: Request) -> str:
    """
    Extract correlation ID from request state or generate a new one.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Correlation ID string
    """
    return getattr(request.state, "correlation_id", uuid.uuid4().hex)


def format_validation_error(
    errors: list,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Format Pydantic validation errors into standardized response.
    
    Args:
        errors: List of validation errors from Pydantic
        correlation_id: Request correlation ID
        
    Returns:
        Standardized error response dictionary
    """
    error_messages = []
    for error in errors:
        if isinstance(error, dict):
            field = error.get("loc", ["unknown"])[-1]
            msg = error.get("msg", "Validation error")
            error_messages.append(f"{field}: {msg}")
        else:
            error_messages.append(str(error))
    
    message = "Validation failed: " + "; ".join(error_messages)
    
    return create_error_response(
        message=message,
        status_code=422,
        correlation_id=correlation_id,
        error_type="ValidationError",
        hint=get_hint_for_status_code(422),
    )
