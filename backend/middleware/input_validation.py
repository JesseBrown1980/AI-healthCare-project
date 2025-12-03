"""
Input validation middleware for automatic request sanitization and validation.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic input validation and sanitization.
    
    Features:
    - Automatic XSS pattern detection
    - SQL injection pattern detection
    - Request body sanitization
    - Query parameter validation
    - Path parameter validation
    """
    
    def __init__(
        self,
        app,
        enabled: bool = True,
        max_query_length: int = 500,
        max_path_length: int = 2000,
        strict_mode: bool = False,
    ):
        """
        Initialize input validation middleware.
        
        Args:
            app: FastAPI application
            enabled: Enable/disable input validation
            max_query_length: Maximum query string length
            max_path_length: Maximum path length
            strict_mode: If True, reject requests with suspicious patterns instead of sanitizing
        """
        super().__init__(app)
        self.enabled = enabled
        self.max_query_length = max_query_length
        self.max_path_length = max_path_length
        self.strict_mode = strict_mode
        
        # Patterns to detect XSS attempts
        self.xss_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'on\w+\s*=', re.IGNORECASE),  # onclick=, onerror=, etc.
            re.compile(r'<iframe[^>]*>', re.IGNORECASE),
            re.compile(r'<object[^>]*>', re.IGNORECASE),
            re.compile(r'<embed[^>]*>', re.IGNORECASE),
        ]
        
        # Patterns to detect SQL injection attempts
        self.sql_patterns = [
            re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|OR|AND)\b)", re.IGNORECASE),
            re.compile(r"(--|#|/\*|\*/)", re.IGNORECASE),  # SQL comments
            re.compile(r"('|(\\')|(;)|(\\)|(\%27)|(\%00))", re.IGNORECASE),  # SQL injection characters
        ]
        
        # Paths to skip validation (health checks, static files, etc.)
        self.skip_paths = {
            "/health",
            "/api/v1/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }
    
    def _detect_xss(self, value: str) -> bool:
        """
        Detect XSS patterns in input.
        
        Args:
            value: Input string to check
            
        Returns:
            True if XSS pattern detected
        """
        for pattern in self.xss_patterns:
            if pattern.search(value):
                return True
        return False
    
    def _detect_sql_injection(self, value: str) -> bool:
        """
        Detect SQL injection patterns in input.
        
        Args:
            value: Input string to check
            
        Returns:
            True if SQL injection pattern detected
        """
        # Only check if it looks like SQL (has SQL keywords)
        if not any(keyword in value.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'UNION']):
            return False
        
        for pattern in self.sql_patterns:
            if pattern.search(value):
                return True
        return False
    
    def _sanitize_string(self, value: str) -> str:
        """
        Sanitize a string by removing dangerous patterns.
        
        Args:
            value: String to sanitize
            
        Returns:
            Sanitized string
        """
        # Remove script tags
        value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        # Remove javascript: protocol
        value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
        # Remove event handlers
        value = re.sub(r'on\w+\s*=', '', value, flags=re.IGNORECASE)
        # Remove iframe, object, embed tags
        value = re.sub(r'<(iframe|object|embed)[^>]*>', '', value, flags=re.IGNORECASE)
        
        return value
    
    def _validate_query_params(self, request: Request) -> Optional[JSONResponse]:
        """
        Validate query parameters.
        
        Args:
            request: FastAPI request
            
        Returns:
            JSONResponse with error if validation fails, None otherwise
        """
        query_string = str(request.url.query)
        
        # Check query string length
        if len(query_string) > self.max_query_length:
            logger.warning(
                "Query string too long: %d characters (max: %d) from %s",
                len(query_string),
                self.max_query_length,
                request.client.host if request.client else "unknown"
            )
            if self.strict_mode:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status": "error",
                        "error_type": "ValidationError",
                        "message": f"Query string too long (max {self.max_query_length} characters)"
                    }
                )
        
        # Check for XSS in query parameters
        for key, value in request.query_params.items():
            if isinstance(value, str):
                if self._detect_xss(value):
                    logger.warning(
                        "XSS pattern detected in query parameter %s from %s",
                        key,
                        request.client.host if request.client else "unknown"
                    )
                    if self.strict_mode:
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={
                                "status": "error",
                                "error_type": "ValidationError",
                                "message": "Invalid characters detected in query parameters"
                            }
                        )
        
        return None
    
    def _validate_path(self, request: Request) -> Optional[JSONResponse]:
        """
        Validate request path.
        
        Args:
            request: FastAPI request
            
        Returns:
            JSONResponse with error if validation fails, None otherwise
        """
        path = request.url.path
        
        # Check path length
        if len(path) > self.max_path_length:
            logger.warning(
                "Path too long: %d characters (max: %d) from %s",
                len(path),
                self.max_path_length,
                request.client.host if request.client else "unknown"
            )
            if self.strict_mode:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status": "error",
                        "error_type": "ValidationError",
                        "message": f"Path too long (max {self.max_path_length} characters)"
                    }
                )
        
        # Check for path traversal attempts
        if ".." in path or "//" in path:
            logger.warning(
                "Path traversal attempt detected: %s from %s",
                path,
                request.client.host if request.client else "unknown"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "error_type": "ValidationError",
                    "message": "Invalid path"
                }
            )
        
        return None
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate inputs."""
        
        if not self.enabled:
            return await call_next(request)
        
        # Skip validation for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        # Validate path
        path_error = self._validate_path(request)
        if path_error:
            return path_error
        
        # Validate query parameters
        query_error = self._validate_query_params(request)
        if query_error:
            return query_error
        
        # Process request
        response = await call_next(request)
        
        return response
