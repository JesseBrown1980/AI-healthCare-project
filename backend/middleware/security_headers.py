"""
Security headers middleware for enhanced application security.

Implements comprehensive security headers including:
- Content Security Policy (CSP)
- HTTP Strict Transport Security (HSTS)
- X-Frame-Options
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable
import os


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Provides defense-in-depth security by adding multiple security headers
    that help protect against common web vulnerabilities.
    """
    
    def __init__(
        self,
        app,
        enabled: bool = True,
        strict_transport_security: bool = True,
        **kwargs
    ):
        super().__init__(app)
        self.enabled = enabled
        self.strict_transport_security_enabled = strict_transport_security
        self.strict_transport_security_max_age = os.getenv(
            "HSTS_MAX_AGE", "31536000"  # 1 year default
        )
        self.enable_csp = os.getenv("ENABLE_CSP", "true").lower() == "true"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to the response.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response with security headers added
        """
        response = await call_next(request)
        
        if not self.enabled:
            return response
        
        # HTTP Strict Transport Security (HSTS)
        # Forces browsers to use HTTPS for future requests
        if self.strict_transport_security_enabled:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.strict_transport_security_max_age}; "
                "includeSubDomains; preload"
            )
        
        # X-Frame-Options
        # Prevents clickjacking attacks by controlling if page can be embedded in frames
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options
        # Prevents MIME type sniffing attacks
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Referrer-Policy
        # Controls how much referrer information is sent with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy (formerly Feature-Policy)
        # Controls which browser features can be used
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=()"
        )
        
        # Content Security Policy (CSP)
        # Controls which resources can be loaded and from where
        if self.enable_csp:
            # Default CSP - can be customized per environment
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Allow inline scripts for development
                "style-src 'self' 'unsafe-inline'; "  # Allow inline styles
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "upgrade-insecure-requests"
            )
            response.headers["Content-Security-Policy"] = csp_policy
        
        # X-XSS-Protection (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Remove server header to avoid information disclosure
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response
