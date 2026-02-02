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
        # Fast bypass check for values that clearly don't look like SQL
        # We look for common SQL keywords or special injection characters like ' or --
        upper_val = value.upper()
        if not any(k in upper_val for k in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'UNION', ' OR ', ' AND ', "'", '--', '#']):
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
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate inputs."""
        if not self.enabled:
            return await call_next(request)
        
        # Allow dynamic override via environment variable
        current_strict = self.strict_mode or os.getenv("INPUT_VALIDATION_STRICT", "false").lower() == "true"
        
        # Skip validation for certain paths
        path = request.url.path
        if any(path.startswith(p) for p in self.skip_paths):
            return await call_next(request)
        
        # Validate path
        path_error = self._validate_path(request, current_strict)
        if path_error:
            return path_error
        
        # Validate query parameters
        query_error = self._validate_query_params(request, current_strict)
        if query_error:
            return query_error
            
        # Validate request body
        body_error = await self._validate_body(request, current_strict)
        if body_error:
            return body_error
        
        # Process request
        return await call_next(request)

    def _validate_path(self, request: Request, strict_mode: bool) -> Optional[JSONResponse]:
        path = request.url.path
        if len(path) > self.max_path_length:
            logger.warning(f"Path too long from {request.client.host if request.client else 'unknown'}")
            if strict_mode:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status": "error",
                        "error_type": "ValidationError",
                        "message": f"Path too long (max {self.max_path_length} characters)"
                    }
                )
        
        if ".." in path or "//" in path:
            logger.warning(f"Path traversal attempt: {path}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status": "error", "message": "Invalid path"}
            )
        return None

    def _validate_query_params(self, request: Request, strict_mode: bool) -> Optional[JSONResponse]:
        for key, value in request.query_params.items():
            if self._detect_xss(value) or self._detect_sql_injection(value):
                logger.warning(f"Malicious pattern in query param '{key}'")
                if strict_mode:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "status": "error",
                            "message": "Malicious patterns detected in request"
                        }
                    )
        return None

    async def _validate_body(self, request: Request, strict_mode: bool) -> Optional[JSONResponse]:
        if request.method not in ("POST", "PUT", "PATCH"):
            return None
        
        content_type = request.headers.get("Content-Type", "").lower()
        if "application/json" not in content_type:
            return None
        
        try:
            body_bytes = await request.body()
            if not body_bytes:
                return None
            
            body_str = body_bytes.decode('utf-8', errors='ignore')
            
            if self._detect_xss(body_str) or self._detect_sql_injection(body_str):
                logger.warning(f"Malicious pattern in request body")
                if strict_mode:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={
                            "status": "error",
                            "message": "Malicious patterns detected in request body"
                        }
                    )
            
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive
            
        except Exception as e:
            logger.error(f"Error validating body: {e}")
            if strict_mode:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"status": "error", "message": "Invalid request body"}
                )
        return None
