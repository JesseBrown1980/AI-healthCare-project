"""
Logging utilities for consistent logging with correlation IDs.

Provides standardized logging functions that automatically include
correlation IDs from request context.
"""

import logging
from typing import Optional, Any, Dict
from fastapi import Request


logger = logging.getLogger(__name__)


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
