"""
Performance monitoring middleware for tracking request timing, slow queries, and error rates.
"""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from datetime import datetime, timezone
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """In-memory storage for performance metrics."""
    
    def __init__(self, max_entries: int = 1000):
        """
        Initialize performance metrics storage.
        
        Args:
            max_entries: Maximum number of entries to keep per metric type
        """
        self.request_times: deque = deque(maxlen=max_entries)
        self.slow_requests: deque = deque(maxlen=max_entries)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.endpoint_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_entries))
        self.slow_query_threshold: float = 1.0  # 1 second default
        
    def record_request(
        self,
        path: str,
        method: str,
        duration: float,
        status_code: int,
        is_error: bool = False
    ) -> None:
        """
        Record a request metric.
        
        Args:
            path: Request path
            method: HTTP method
            duration: Request duration in seconds
            status_code: HTTP status code
            is_error: Whether this was an error response
        """
        endpoint = f"{method} {path}"
        
        # Record all request times
        self.request_times.append({
            "endpoint": endpoint,
            "duration": duration,
            "status_code": status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Record endpoint-specific times
        self.endpoint_times[endpoint].append(duration)
        
        # Track slow requests
        if duration >= self.slow_query_threshold:
            self.slow_requests.append({
                "endpoint": endpoint,
                "duration": duration,
                "status_code": status_code,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            logger.warning(
                "Slow request detected: %s took %.3fs (threshold: %.3fs)",
                endpoint,
                duration,
                self.slow_query_threshold
            )
        
        # Track errors
        if is_error or status_code >= 400:
            error_key = f"{endpoint}:{status_code}"
            self.error_counts[error_key] += 1
    
    def get_stats(self) -> Dict:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.request_times:
            return {
                "total_requests": 0,
                "average_duration": 0,
                "slow_requests_count": 0,
                "error_count": sum(self.error_counts.values()),
                "endpoint_stats": {}
            }
        
        durations = [r["duration"] for r in self.request_times]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        
        # Calculate endpoint-specific stats
        endpoint_stats = {}
        for endpoint, times in self.endpoint_times.items():
            if times:
                endpoint_times_list = list(times)
                endpoint_stats[endpoint] = {
                    "count": len(endpoint_times_list),
                    "average": sum(endpoint_times_list) / len(endpoint_times_list),
                    "min": min(endpoint_times_list),
                    "max": max(endpoint_times_list)
                }
        
        return {
            "total_requests": len(self.request_times),
            "average_duration": avg_duration,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "slow_requests_count": len(self.slow_requests),
            "error_count": sum(self.error_counts.values()),
            "error_breakdown": dict(self.error_counts),
            "endpoint_stats": endpoint_stats,
            "slow_requests": list(self.slow_requests)[-10:],  # Last 10 slow requests
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.request_times.clear()
        self.slow_requests.clear()
        self.error_counts.clear()
        self.endpoint_times.clear()


# Global metrics instance
_metrics = PerformanceMetrics()


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for monitoring request performance.
    
    Tracks:
    - Request duration
    - Slow requests (configurable threshold)
    - Error rates by endpoint
    - Endpoint-specific statistics
    """
    
    def __init__(
        self,
        app: ASGIApp,
        enabled: bool = True,
        slow_request_threshold: float = 1.0,
        track_slow_queries: bool = True,
    ):
        """
        Initialize performance monitoring middleware.
        
        Args:
            app: FastAPI application
            enabled: Enable/disable performance monitoring
            slow_request_threshold: Threshold in seconds for slow requests
            track_slow_queries: Whether to track slow database queries
        """
        super().__init__(app)
        self.enabled = enabled
        self.metrics = _metrics
        self.metrics.slow_query_threshold = slow_request_threshold
        self.track_slow_queries = track_slow_queries
        
        # Endpoints to skip monitoring
        self.skip_paths = {
            "/health",
            "/api/v1/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and track performance metrics."""
        
        if not self.enabled:
            return await call_next(request)
        
        # Skip monitoring for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Determine if error
            is_error = response.status_code >= 400
            
            # Record metrics
            self.metrics.record_request(
                path=request.url.path,
                method=request.method,
                duration=duration,
                status_code=response.status_code,
                is_error=is_error
            )
            
            # Add performance headers
            response.headers["X-Request-Duration"] = f"{duration:.3f}"
            response.headers["X-Request-Id"] = getattr(request.state, "correlation_id", "")
            
            # Log slow requests with structured logging
            if duration >= self.metrics.slow_query_threshold:
                from backend.utils.logging_utils import log_structured
                correlation_id = getattr(request.state, "correlation_id", "")
                log_structured(
                    level="warning",
                    message="Slow request detected",
                    correlation_id=correlation_id,
                    request=request,
                    duration_ms=duration * 1000,
                    threshold_ms=self.metrics.slow_query_threshold * 1000,
                    endpoint=f"{request.method} {request.url.path}",
                    status_code=response.status_code
                )
            
            return response
            
        except Exception as e:
            # Record error even if exception occurs
            duration = time.time() - start_time
            self.metrics.record_request(
                path=request.url.path,
                method=request.method,
                duration=duration,
                status_code=500,
                is_error=True
            )
            raise


def get_performance_metrics() -> PerformanceMetrics:
    """
    Get the global performance metrics instance.
    
    Returns:
        PerformanceMetrics instance
    """
    return _metrics


def reset_performance_metrics() -> None:
    """Reset all performance metrics."""
    _metrics.reset()
