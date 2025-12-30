"""
Request timeout middleware to prevent long-running requests from blocking the server.
"""

import logging
import asyncio
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Request timeout middleware.
    
    Automatically cancels requests that exceed the configured timeout.
    """
    
    def __init__(
        self,
        app,
        timeout_seconds: float = 30.0,
        enabled: bool = True,
    ):
        """
        Initialize timeout middleware.
        
        Args:
            app: FastAPI application
            timeout_seconds: Maximum request duration in seconds
            enabled: Enable/disable timeout middleware
        """
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled
        
        # Endpoints that may need longer timeouts
        self.long_timeout_endpoints = {
            "/api/v1/analyze-patient": 120.0,  # Patient analysis can take time
            "/api/v1/documents/upload": 60.0,  # File uploads
            "/api/v1/documents/process": 180.0,  # OCR processing
            "/api/v1/query": 60.0,  # LLM queries
        }
    
    def _get_timeout_for_path(self, path: str) -> float:
        """Get timeout for specific endpoint."""
        for endpoint, timeout in self.long_timeout_endpoints.items():
            if path.startswith(endpoint):
                return timeout
        return self.timeout_seconds
    
    async def dispatch(self, request: Request, call_next):
        """Process request with timeout."""
        if not self.enabled:
            return await call_next(request)
        
        # Get timeout for this endpoint
        timeout = self._get_timeout_for_path(request.url.path)
        
        # Skip timeout for health checks
        if request.url.path in ["/health", "/api/v1/health"]:
            return await call_next(request)
        
        try:
            # Run request with timeout
            response = await asyncio.wait_for(
                call_next(request),
                timeout=timeout
            )
            return response
            
        except asyncio.TimeoutError:
            logger.warning(
                "Request timeout for %s %s (timeout: %.1fs)",
                request.method,
                request.url.path,
                timeout
            )
            
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "status": "error",
                    "message": f"Request timeout: operation exceeded {timeout} seconds",
                    "error_type": "timeout",
                    "path": str(request.url.path),
                    "timeout_seconds": timeout,
                },
                headers={
                    "Retry-After": "30",  # Suggest retry after 30 seconds
                }
            )
        
        except Exception as e:
            logger.error(
                "Error in timeout middleware for %s: %s",
                request.url.path,
                str(e)
            )
            # Re-raise to let other error handlers deal with it
            raise

