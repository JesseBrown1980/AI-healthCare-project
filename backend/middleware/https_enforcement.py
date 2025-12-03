"""
HTTPS enforcement middleware for production security.

Enforces HTTPS connections in production environments based on compliance policies.
"""

import logging
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from typing import Callable

from backend.config.compliance_policies import get_compliance_policy

logger = logging.getLogger(__name__)


class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce HTTPS connections in production.
    
    Redirects HTTP requests to HTTPS when:
    - enforce_https is enabled in compliance policy
    - Running in production environment
    - Request is not already HTTPS
    """
    
    def __init__(
        self,
        app,
        enabled: bool = True,
        production_mode: bool = None,
        **kwargs
    ):
        """
        Initialize HTTPS enforcement middleware.
        
        Args:
            app: FastAPI application
            enabled: Enable/disable HTTPS enforcement
            production_mode: Whether running in production (auto-detected if None)
        """
        super().__init__(app)
        self.enabled = enabled
        
        # Auto-detect production mode if not specified
        if production_mode is None:
            env = os.getenv("ENVIRONMENT", "development").lower()
            self.production_mode = env in ["production", "prod", "staging"]
        else:
            self.production_mode = production_mode
        
        # Paths to skip HTTPS enforcement (health checks, etc.)
        self.skip_paths = {
            "/health",
            "/api/v1/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Enforce HTTPS for requests.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response (redirected to HTTPS if needed)
        """
        # Skip if disabled
        if not self.enabled:
            return await call_next(request)
        
        # Skip certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        # Check compliance policy
        policy = get_compliance_policy()
        if not policy.enforce_https:
            return await call_next(request)
        
        # Only enforce in production
        if not self.production_mode:
            logger.debug("HTTPS enforcement skipped (not in production mode)")
            return await call_next(request)
        
        # Check if request is already HTTPS
        scheme = request.url.scheme.lower()
        if scheme == "https":
            return await call_next(request)
        
        # Check X-Forwarded-Proto header (for reverse proxies)
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()
        if forwarded_proto == "https":
            return await call_next(request)
        
        # Redirect HTTP to HTTPS
        https_url = request.url.replace(scheme="https", port=443)
        
        logger.warning(
            f"HTTPS enforcement: Redirecting HTTP request to HTTPS: {request.url.path}"
        )
        
        return RedirectResponse(
            url=str(https_url),
            status_code=301,  # Permanent redirect
        )
