"""
Rate limiting middleware to protect API from abuse.

Supports both in-memory and Redis-backed rate limiting for distributed systems.
Implements per-user and per-IP rate limiting with comprehensive headers.
"""

import logging
import time
from collections import defaultdict
from typing import Dict, Tuple, Optional, Set
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Configuration for rate limiting a specific endpoint."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.
    
    Limits requests per IP address and per user (if authenticated).
    Supports per-endpoint limits, per-user limits, admin bypass, and Redis backend.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10,
        enabled: bool = True,
        use_redis: bool = False,
        user_requests_per_minute: Optional[int] = None,
        user_requests_per_hour: Optional[int] = None,
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            requests_per_minute: Default max requests per minute per IP/user
            requests_per_hour: Default max requests per hour per IP/user
            burst_size: Default max requests in short burst (sliding 10-second window)
            enabled: Enable/disable rate limiting
            use_redis: Use Redis for distributed rate limiting (if available)
            user_requests_per_minute: Separate limit for authenticated users (None = same as IP limit)
            user_requests_per_hour: Separate limit for authenticated users (None = same as IP limit)
        """
        super().__init__(app)
        self.default_requests_per_minute = requests_per_minute
        self.default_requests_per_hour = requests_per_hour
        self.default_burst_size = burst_size
        self.enabled = enabled
        self.use_redis = use_redis
        
        # Per-user limits (if different from IP limits)
        self.user_requests_per_minute = user_requests_per_minute or requests_per_minute
        self.user_requests_per_hour = user_requests_per_hour or requests_per_hour
        
        # Per-endpoint rate limit configurations
        self._endpoint_limits: Dict[str, RateLimitConfig] = {
            # More restrictive for write operations
            "/api/v1/analyze-patient": RateLimitConfig(30, 500, 5),
            "/api/v1/documents/upload": RateLimitConfig(20, 200, 3),
            "/api/v1/query": RateLimitConfig(40, 800, 8),
            "/api/v1/oauth": RateLimitConfig(10, 100, 2),  # OAuth endpoints
            # More permissive for read operations
            "/api/v1/patients": RateLimitConfig(120, 2000, 20),
            "/api/v1/health": RateLimitConfig(300, 10000, 50),
        }
        
        # Admin roles that bypass rate limiting
        self._admin_roles: Set[str] = {"admin", "system"}
        
        # Redis client (if available)
        self._redis_client = None
        if use_redis:
            try:
                from backend.database.connection import get_redis_client
                self._redis_client = get_redis_client()
                if self._redis_client:
                    logger.info("Using Redis for distributed rate limiting")
                else:
                    logger.warning("Redis requested but not available, falling back to in-memory")
                    self.use_redis = False
            except Exception as e:
                logger.warning(f"Failed to initialize Redis for rate limiting: {e}, using in-memory")
                self.use_redis = False
        
        # In-memory storage (fallback if Redis not available)
        self._request_times: Dict[str, list] = defaultdict(list)
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Clean up every 5 minutes
        
    def _get_client_id(self, request: Request) -> str:
        """Get unique identifier for rate limiting (IP or user ID)."""
        # Prefer authenticated user ID if available
        auth = getattr(request.state, "auth", None)
        if auth:
            # Check for user_id in TokenContext
            user_id = getattr(auth, "user_id", None) or getattr(auth, "subject", None)
            if user_id:
                return f"user:{user_id}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP from X-Forwarded-For header
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _is_admin_user(self, request: Request) -> bool:
        """Check if the user is an admin (bypasses rate limiting)."""
        auth = getattr(request.state, "auth", None)
        if not auth:
            return False
        
        # Check for admin roles in TokenContext
        roles = getattr(auth, "clinician_roles", set()) or getattr(auth, "roles", set())
        if isinstance(roles, (list, tuple)):
            roles = set(roles)
        
        return bool(self._admin_roles.intersection(roles)) if roles else False
    
    def _get_rate_limit_config(self, path: str, is_authenticated: bool = False) -> RateLimitConfig:
        """
        Get rate limit configuration for a specific endpoint.
        
        Args:
            path: Request path
            is_authenticated: Whether the user is authenticated
            
        Returns:
            RateLimitConfig with appropriate limits
        """
        # Check for exact path match first
        if path in self._endpoint_limits:
            base_config = self._endpoint_limits[path]
        else:
            # Check for path prefix matches (for parameterized routes)
            base_config = None
            for endpoint, config in self._endpoint_limits.items():
                if path.startswith(endpoint):
                    base_config = config
                    break
            
            # Return default configuration if no match
            if not base_config:
                base_config = RateLimitConfig(
                    self.default_requests_per_minute,
                    self.default_requests_per_hour,
                    self.default_burst_size,
                )
        
        # Apply per-user limits if authenticated and different from IP limits
        if is_authenticated and (
            self.user_requests_per_minute != self.default_requests_per_minute or
            self.user_requests_per_hour != self.default_requests_per_hour
        ):
            return RateLimitConfig(
                min(base_config.requests_per_minute, self.user_requests_per_minute),
                min(base_config.requests_per_hour, self.user_requests_per_hour),
                base_config.burst_size,
            )
        
        return base_config
    
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
    
    async def _check_rate_limit_redis(
        self,
        client_id: str,
        config: RateLimitConfig,
    ) -> Tuple[bool, Optional[str], int, int]:
        """
        Check rate limit using Redis (distributed rate limiting).
        
        Returns:
            (allowed, error_message, remaining_minute, remaining_hour)
        """
        if not self._redis_client:
            # Fallback to in-memory if Redis unavailable
            return await self._check_rate_limit_memory(client_id, config)
        
        try:
            current_time = int(time.time())
            current_time_ms = int(time.time() * 1000)
            
            # Redis keys
            key_minute = f"ratelimit:{client_id}:minute"
            key_hour = f"ratelimit:{client_id}:hour"
            key_burst = f"ratelimit:{client_id}:burst"
            
            # Check burst limit (10 second window)
            burst_count = await self._redis_client.zcount(
                key_burst,
                current_time_ms - 10000,
                current_time_ms
            )
            if burst_count >= config.burst_size:
                return False, f"Burst limit exceeded: {config.burst_size} requests per 10 seconds", 0, 0
            
            # Check per-minute limit
            minute_count = await self._redis_client.zcount(
                key_minute,
                current_time - 60,
                current_time
            )
            remaining_minute = max(0, config.requests_per_minute - minute_count)
            if minute_count >= config.requests_per_minute:
                # Get oldest request in window
                oldest = await self._redis_client.zrange(key_minute, 0, 0, withscores=True)
                if oldest:
                    oldest_time = int(oldest[0][1])
                    remaining = max(1, 60 - (current_time - oldest_time))
                else:
                    remaining = 60
                return False, f"Rate limit exceeded: {config.requests_per_minute} requests per minute. Try again in {remaining} seconds", 0, 0
            
            # Check per-hour limit
            hour_count = await self._redis_client.zcount(
                key_hour,
                current_time - 3600,
                current_time
            )
            remaining_hour = max(0, config.requests_per_hour - hour_count)
            if hour_count >= config.requests_per_hour:
                oldest = await self._redis_client.zrange(key_hour, 0, 0, withscores=True)
                if oldest:
                    oldest_time = int(oldest[0][1])
                    remaining = max(1, 3600 - (current_time - oldest_time))
                else:
                    remaining = 3600
                return False, f"Rate limit exceeded: {config.requests_per_hour} requests per hour. Try again in {remaining} seconds", 0, 0
            
            # Add current request to Redis
            pipe = self._redis_client.pipeline()
            pipe.zadd(key_minute, {str(current_time_ms): current_time})
            pipe.zadd(key_hour, {str(current_time_ms): current_time})
            pipe.zadd(key_burst, {str(current_time_ms): current_time_ms})
            pipe.expire(key_minute, 120)  # Keep for 2 minutes
            pipe.expire(key_hour, 7200)  # Keep for 2 hours
            pipe.expire(key_burst, 20)  # Keep for 20 seconds
            await pipe.execute()
            
            return True, None, remaining_minute, remaining_hour
            
        except Exception as e:
            logger.warning(f"Redis rate limit check failed: {e}, falling back to in-memory")
            return await self._check_rate_limit_memory(client_id, config)
    
    async def _check_rate_limit_memory(
        self,
        client_id: str,
        config: RateLimitConfig,
    ) -> Tuple[bool, Optional[str], int, int]:
        """
        Check rate limit using in-memory storage.
        
        Returns:
            (allowed, error_message, remaining_minute, remaining_hour)
        """
        current_time = time.time()
        request_times = self._request_times[client_id]
        
        # Remove timestamps older than 1 hour
        cutoff_time = current_time - 3600
        request_times[:] = [ts for ts in request_times if ts > cutoff_time]
        
        # Check burst limit (last 10 seconds)
        recent_requests = [ts for ts in request_times if ts > current_time - 10]
        if len(recent_requests) >= config.burst_size:
            return False, f"Burst limit exceeded: {config.burst_size} requests per 10 seconds", 0, 0
        
        # Check per-minute limit
        minute_requests = [ts for ts in request_times if ts > current_time - 60]
        remaining_minute = max(0, config.requests_per_minute - len(minute_requests))
        if len(minute_requests) >= config.requests_per_minute:
            remaining = 60 - int(current_time - minute_requests[0])
            return False, f"Rate limit exceeded: {config.requests_per_minute} requests per minute. Try again in {remaining} seconds", 0, 0
        
        # Check per-hour limit
        hour_requests = [ts for ts in request_times if ts > current_time - 3600]
        remaining_hour = max(0, config.requests_per_hour - len(hour_requests))
        if len(hour_requests) >= config.requests_per_hour:
            remaining = 3600 - int(current_time - hour_requests[0])
            return False, f"Rate limit exceeded: {config.requests_per_hour} requests per hour. Try again in {remaining} seconds", 0, 0
        
        # Add current request timestamp
        request_times.append(current_time)
        return True, None, remaining_minute, remaining_hour
    
    async def _check_rate_limit(
        self,
        client_id: str,
        config: RateLimitConfig,
    ) -> Tuple[bool, Optional[str], int, int]:
        """
        Check if request should be rate limited.
        
        Returns:
            (allowed, error_message, remaining_minute, remaining_hour)
        """
        if not self.enabled:
            return True, None, config.requests_per_minute, config.requests_per_hour
        
        if self.use_redis and self._redis_client:
            return await self._check_rate_limit_redis(client_id, config)
        else:
            return await self._check_rate_limit_memory(client_id, config)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/api/v1/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Skip rate limiting in test environment
        import os
        if os.getenv("TESTING", "").lower() == "true" or os.getenv("PYTEST_CURRENT_TEST"):
            return await call_next(request)
        
        # Check if user is admin (bypass rate limiting)
        if self._is_admin_user(request):
            response = await call_next(request)
            # Still add headers for admin users (for monitoring)
            response.headers["X-RateLimit-Limit"] = "unlimited"
            response.headers["X-RateLimit-Remaining"] = "unlimited"
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
            return response
        
        # Cleanup old entries periodically
        self._cleanup_old_entries()
        
        # Get rate limit configuration for this endpoint
        path = request.url.path
        is_authenticated = bool(getattr(request.state, "auth", None))
        config = self._get_rate_limit_config(path, is_authenticated)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        allowed, error_msg, remaining_minute, remaining_hour = await self._check_rate_limit(client_id, config)
        
        if not allowed:
            logger.warning(
                "Rate limit exceeded for %s at %s (limit: %d/min)",
                client_id,
                path,
                config.requests_per_minute
            )
            
            # Calculate retry-after time
            current_time = time.time()
            request_times = self._request_times[client_id]
            minute_requests = [ts for ts in request_times if ts > current_time - 60]
            if minute_requests:
                retry_after = max(1, 60 - int(current_time - minute_requests[0]))
            else:
                retry_after = 60
            
            # Calculate reset time
            current_time = time.time()
            reset_time = int(current_time) + 60  # Reset in 1 minute
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "error",
                    "message": error_msg or "Rate limit exceeded",
                    "error_type": "rate_limit_exceeded",
                    "path": path,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(config.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "X-RateLimit-Limit-Hour": str(config.requests_per_hour),
                    "X-RateLimit-Remaining-Hour": "0",
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add comprehensive rate limit headers (RFC 6585 compliant)
        current_time = time.time()
        reset_time = int(current_time) + 60  # Reset in 1 minute
        
        response.headers["X-RateLimit-Limit"] = str(config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining_minute)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        response.headers["X-RateLimit-Limit-Hour"] = str(config.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_hour)
        response.headers["X-RateLimit-Policy"] = f"{config.requests_per_minute};w=60,{config.requests_per_hour};w=3600"
        
        return response

