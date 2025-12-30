"""
Rate limiting middleware to protect API from abuse.
"""

import logging
import time
from collections import defaultdict
from typing import Dict, Tuple, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.
    
    Limits requests per IP address and per user (if authenticated).
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
        enabled: bool = True,
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            requests_per_minute: Max requests per minute per IP/user
            requests_per_hour: Max requests per hour per IP/user
            burst_size: Max requests in short burst (sliding 10-second window)
            enabled: Enable/disable rate limiting
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        self.enabled = enabled
        
        # In-memory storage (use Redis in production)
        self._request_times: Dict[str, list] = defaultdict(list)
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Clean up every 5 minutes
        
    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for rate limiting (IP or user ID)."""
        # Prefer authenticated user ID if available
        auth = getattr(request.state, "auth", None)
        if auth and hasattr(auth, "user_id") and auth.user_id:
            return f"user:{auth.user_id}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP from X-Forwarded-For header
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _cleanup_old_entries(self):
        """Remove old request timestamps to prevent memory leak."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = current_time - 3600  # Keep last hour
        for client_id in list(self._request_times.keys()):
            self._request_times[client_id] = [
                ts for ts in self._request_times[client_id] if ts > cutoff_time
            ]
            if not self._request_times[client_id]:
                del self._request_times[client_id]
        
        self._last_cleanup = current_time
    
    def _check_rate_limit(self, client_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request should be rate limited.
        
        Returns:
            (allowed, error_message)
        """
        if not self.enabled:
            return True, None
        
        current_time = time.time()
        request_times = self._request_times[client_id]
        
        # Remove timestamps older than 1 hour
        cutoff_time = current_time - 3600
        request_times[:] = [ts for ts in request_times if ts > cutoff_time]
        
        # Check burst limit (last 10 seconds)
        recent_requests = [ts for ts in request_times if ts > current_time - 10]
        if len(recent_requests) >= self.burst_size:
            return False, f"Burst limit exceeded: {self.burst_size} requests per 10 seconds"
        
        # Check per-minute limit
        minute_requests = [ts for ts in request_times if ts > current_time - 60]
        if len(minute_requests) >= self.requests_per_minute:
            remaining = 60 - int(current_time - minute_requests[0])
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute. Try again in {remaining} seconds"
        
        # Check per-hour limit
        if len(request_times) >= self.requests_per_hour:
            remaining = 3600 - int(current_time - request_times[0])
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour. Try again in {remaining} seconds"
        
        # Add current request timestamp
        request_times.append(current_time)
        return True, None
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/api/v1/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Cleanup old entries periodically
        self._cleanup_old_entries()
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        allowed, error_msg = self._check_rate_limit(client_id)
        
        if not allowed:
            logger.warning(
                "Rate limit exceeded for %s at %s",
                client_id,
                request.url.path
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "error",
                    "message": error_msg or "Rate limit exceeded",
                    "error_type": "rate_limit_exceeded",
                    "path": str(request.url.path),
                },
                headers={
                    "Retry-After": "60",  # Suggest retry after 60 seconds
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        request_times = self._request_times[client_id]
        current_time = time.time()
        minute_requests = [ts for ts in request_times if ts > current_time - 60]
        remaining = max(0, self.requests_per_minute - len(minute_requests))
        
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time) + 60)
        
        return response

