"""
Logging utilities for consistent logging with correlation IDs.

Provides standardized logging functions that automatically include
correlation IDs from request context. Supports both text and structured (JSON) logging.
"""

import logging
import json
import os
from typing import Optional, Any, Dict
from datetime import datetime, timezone
from fastapi import Request


logger = logging.getLogger(__name__)

# Check if structured logging is enabled
USE_STRUCTURED_LOGGING = os.getenv("STRUCTURED_LOGGING", "false").lower() == "true"


def get_correlation_id_from_request(request: Optional[Request]) -> str:
    """
    Extract correlation ID from request state or return empty string.
    
    Args:
        request: FastAPI request object (may be None)
        
    Returns:
        Correlation ID string or empty string if not available
    """
    if request is None:
        return ""
    return getattr(request.state, "correlation_id", "")


def log_with_correlation(
    level: str,
    message: str,
    correlation_id: Optional[str] = None,
    request: Optional[Request] = None,
    **kwargs
) -> None:
    """
    Log a message with correlation ID.
    
    Args:
        level: Log level ('info', 'warning', 'error', 'debug')
        message: Log message
        correlation_id: Correlation ID (extracted from request if not provided)
        request: FastAPI request object (used to extract correlation ID)
        **kwargs: Additional context to include in log message
    """
    # Get correlation ID
    if correlation_id is None:
        correlation_id = get_correlation_id_from_request(request)
    
    # Format message with correlation ID
    if correlation_id:
        formatted_message = f"[{correlation_id}] {message}"
    else:
        formatted_message = message
    
    # Add additional context if provided
    if kwargs:
        context_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        formatted_message = f"{formatted_message} ({context_str})"
    
    # Log at appropriate level
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(formatted_message)


def log_info(message: str, correlation_id: Optional[str] = None, request: Optional[Request] = None, **kwargs) -> None:
    """Log info message with correlation ID."""
    log_with_correlation("info", message, correlation_id, request, **kwargs)


def log_warning(message: str, correlation_id: Optional[str] = None, request: Optional[Request] = None, **kwargs) -> None:
    """Log warning message with correlation ID."""
    log_with_correlation("warning", message, correlation_id, request, **kwargs)


def log_error(message: str, correlation_id: Optional[str] = None, request: Optional[Request] = None, exc_info: bool = False, **kwargs) -> None:
    """Log error message with correlation ID."""
    correlation_id = correlation_id or get_correlation_id_from_request(request)
    formatted_message = f"[{correlation_id}] {message}" if correlation_id else message
    
    if kwargs:
        context_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        formatted_message = f"{formatted_message} ({context_str})"
    
    logger.error(formatted_message, exc_info=exc_info)


def log_debug(message: str, correlation_id: Optional[str] = None, request: Optional[Request] = None, **kwargs) -> None:
    """Log debug message with correlation ID."""
    log_with_correlation("debug", message, correlation_id, request, **kwargs)


def log_structured(
    level: str,
    message: str,
    correlation_id: Optional[str] = None,
    request: Optional[Request] = None,
    **kwargs
) -> None:
    """
    Log a structured message in JSON format.
    
    Args:
        level: Log level ('info', 'warning', 'error', 'debug')
        message: Log message
        correlation_id: Correlation ID (extracted from request if not provided)
        request: FastAPI request object (used to extract correlation ID)
        **kwargs: Additional structured fields to include
    """
    if correlation_id is None:
        correlation_id = get_correlation_id_from_request(request)
    
    # Build structured log entry
    log_entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "message": message,
        "correlation_id": correlation_id or "",
    }
    
    # Add request context if available
    if request:
        log_entry.update({
            "method": request.method,
            "path": str(request.url.path),
            "client_ip": request.client.host if request.client else None,
        })
    
    # Add additional context
    log_entry.update(kwargs)
    
    # Log as JSON string if structured logging is enabled, otherwise format nicely
    if USE_STRUCTURED_LOGGING:
        log_message = json.dumps(log_entry)
    else:
        # Format as readable text
        parts = [f"[{log_entry['timestamp']}]", f"[{log_entry['level']}]"]
        if correlation_id:
            parts.append(f"[{correlation_id}]")
        parts.append(message)
        if kwargs:
            context_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            parts.append(f"({context_str})")
        log_message = " ".join(parts)
    
    # Log at appropriate level
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(log_message)


def log_request(
    request: Request,
    level: str = "info",
    message: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log HTTP request with full context.
    
    Args:
        request: FastAPI request object
        level: Log level
        message: Optional custom message
        **kwargs: Additional context
    """
    correlation_id = get_correlation_id_from_request(request)
    msg = message or f"{request.method} {request.url.path}"
    
    log_structured(
        level=level,
        message=msg,
        correlation_id=correlation_id,
        request=request,
        **kwargs
    )


def log_service_error(
    error: Exception,
    context: Dict[str, Any],
    correlation_id: Optional[str] = None,
    request: Optional[Request] = None,
) -> None:
    """
    Log service error with full context for debugging.
    
    Args:
        error: Exception that occurred
        context: Additional context about the error
        correlation_id: Correlation ID
        request: FastAPI request object
    """
    if correlation_id is None:
        correlation_id = get_correlation_id_from_request(request)
    
    log_structured(
        level="error",
        message=f"Service error: {type(error).__name__}: {str(error)}",
        correlation_id=correlation_id,
        request=request,
        error_type=type(error).__name__,
        error_message=str(error),
        **context
    )
    
    # Also log with exception info
    logger.error(
        f"[{correlation_id}] Service error: {type(error).__name__}: {str(error)}",
        exc_info=True,
        extra=context
    )
