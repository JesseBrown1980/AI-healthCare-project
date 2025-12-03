"""
Service error handler for standardized error handling across services.

Provides consistent error handling patterns for service layer operations.
"""

from typing import Any, Dict, Optional, Callable, TypeVar, Awaitable
from fastapi import HTTPException, Request
from backend.utils.error_responses import (
    create_error_response,
    create_http_exception,
    get_correlation_id,
)
from backend.utils.logging_utils import log_service_error
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceErrorHandler:
    """
    Standardized error handler for service operations.
    
    Provides consistent error handling with proper logging and error responses.
    """
    
    @staticmethod
    def handle_service_error(
        error: Exception,
        context: Dict[str, Any],
        correlation_id: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> HTTPException:
        """
        Handle a service error and return appropriate HTTPException.
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
            correlation_id: Request correlation ID
            request: FastAPI request object
            
        Returns:
            HTTPException with standardized error response
        """
        if correlation_id is None and request:
            correlation_id = get_correlation_id(request)
        
        # Log the error
        log_service_error(error, context, correlation_id, request)
        
        # Determine error type and status code
        error_type = type(error).__name__
        status_code = 500
        error_message = "An internal error occurred"
        
        # Map common exceptions to appropriate status codes
        if isinstance(error, ValueError):
            status_code = 400
            error_message = str(error) or "Invalid input value"
        elif isinstance(error, KeyError):
            status_code = 404
            error_message = f"Resource not found: {str(error)}"
        elif isinstance(error, PermissionError):
            status_code = 403
            error_message = "Permission denied"
        elif isinstance(error, TimeoutError):
            status_code = 504
            error_message = "Request timeout"
        elif isinstance(error, ConnectionError):
            status_code = 503
            error_message = "Service temporarily unavailable"
        else:
            # For unknown errors, use generic message in production
            import os
            is_debug = os.getenv("DEBUG", "False").lower() == "true"
            if is_debug:
                error_message = f"{error_type}: {str(error)}"
        
        return create_http_exception(
            message=error_message,
            status_code=status_code,
            error_type=error_type,
        )
    
    @staticmethod
    async def handle_async_service_call(
        func: Callable[..., Awaitable[T]],
        context: Dict[str, Any],
        correlation_id: Optional[str] = None,
        request: Optional[Request] = None,
        *args,
        **kwargs
    ) -> T:
        """
        Execute an async service call with standardized error handling.
        
        Args:
            func: Async function to execute
            context: Context for error logging
            correlation_id: Request correlation ID
            request: FastAPI request object
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            HTTPException: If an error occurs
        """
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            # Handle other exceptions
            raise ServiceErrorHandler.handle_service_error(
                e, context, correlation_id, request
            )
    
    @staticmethod
    def handle_sync_service_call(
        func: Callable[..., T],
        context: Dict[str, Any],
        correlation_id: Optional[str] = None,
        request: Optional[Request] = None,
        *args,
        **kwargs
    ) -> T:
        """
        Execute a sync service call with standardized error handling.
        
        Args:
            func: Function to execute
            context: Context for error logging
            correlation_id: Request correlation ID
            request: FastAPI request object
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            HTTPException: If an error occurs
        """
        try:
            return func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            # Handle other exceptions
            raise ServiceErrorHandler.handle_service_error(
                e, context, correlation_id, request
            )


def handle_service_operation(
    operation_name: str,
    correlation_id: Optional[str] = None,
    request: Optional[Request] = None,
):
    """
    Decorator for handling service operations with standardized error handling.
    
    Usage:
        @handle_service_operation("fetch_patient_data")
        async def fetch_patient_data(patient_id: str):
            # Service logic here
            pass
    """
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            context = {
                "operation": operation_name,
                "function": func.__name__,
            }
            return await ServiceErrorHandler.handle_async_service_call(
                func, context, correlation_id, request, *args, **kwargs
            )
        
        def sync_wrapper(*args, **kwargs):
            context = {
                "operation": operation_name,
                "function": func.__name__,
            }
            return ServiceErrorHandler.handle_sync_service_call(
                func, context, correlation_id, request, *args, **kwargs
            )
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
