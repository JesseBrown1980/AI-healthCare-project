"""
Security headers middleware for production security.
"""

import logging
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Implements security best practices for healthcare applications.
    """
    
    def __init__(
        self,
        app,
        enabled: bool = True,
        strict_transport_security: bool = True,
        content_security_policy: Optional[str] = None,
    ):
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application
            enabled: Enable/disable security headers
            strict_transport_security: Enable HSTS (HTTPS only)
            content_security_policy: Custom CSP (defaults to permissive for API)
        """
        super().__init__(app)
        self.enabled = enabled
        self.strict_transport_security = strict_transport_security
        
        # Default CSP for API (permissive since it's an API, not a web page)
        self.content_security_policy = content_security_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        if not self.enabled:
            return response
        
        # Security headers
        security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable XSS protection (legacy but still useful)
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy (restrict browser features)
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=()"
            ),
        }
        
        # Content Security Policy
        if self.content_security_policy:
            security_headers["Content-Security-Policy"] = self.content_security_policy
        
        # Strict Transport Security (only for HTTPS)
        if self.strict_transport_security:
            # Check if request is HTTPS (in production)
            is_https = (
                request.url.scheme == "https" or
                request.headers.get("X-Forwarded-Proto") == "https"
            )
            if is_https:
                security_headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )
        
        # Add headers to response
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response

