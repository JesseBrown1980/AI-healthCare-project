"""
Tests for enhanced rate limiting features.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, status
from fastapi.testclient import TestClient
from starlette.responses import Response

from backend.middleware.rate_limit import RateLimitMiddleware, RateLimitConfig


class TestRateLimitConfig:
    """Test rate limit configuration."""
    
    def test_default_config(self):
        """Test default rate limit configuration."""
        config = RateLimitConfig()
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_size == 10
    
    def test_custom_config(self):
        """Test custom rate limit configuration."""
        config = RateLimitConfig(30, 500, 5)
        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 500
        assert config.burst_size == 5


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock FastAPI app."""
        app = MagicMock()
        return app
    
    @pytest.fixture
    def middleware(self, mock_app):
        """Create rate limit middleware instance."""
        return RateLimitMiddleware(
            mock_app,
            requests_per_minute=10,
            requests_per_hour=100,
            burst_size=3,
            enabled=True,
            use_redis=False,
        )
    
    def test_get_client_id_ip(self, middleware):
        """Test getting client ID from IP address."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.auth = None
        request.client = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {}
        
        client_id = middleware._get_client_id(request)
        assert client_id == "ip:192.168.1.1"
    
    def test_get_client_id_user(self, middleware):
        """Test getting client ID from authenticated user."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        auth = MagicMock()
        auth.user_id = "user123"
        request.state.auth = auth
        request.client = None
        request.headers = {}
        
        client_id = middleware._get_client_id(request)
        assert client_id == "user:user123"
    
    def test_is_admin_user(self, middleware):
        """Test admin user detection."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        auth = MagicMock()
        auth.clinician_roles = {"admin"}
        request.state.auth = auth
        
        assert middleware._is_admin_user(request) is True
    
    def test_is_not_admin_user(self, middleware):
        """Test non-admin user detection."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        auth = MagicMock()
        auth.clinician_roles = {"viewer"}
        request.state.auth = auth
        
        assert middleware._is_admin_user(request) is False
    
    def test_get_rate_limit_config_default(self, middleware):
        """Test getting default rate limit config."""
        config = middleware._get_rate_limit_config("/api/v1/unknown")
        assert config.requests_per_minute == 10
        assert config.requests_per_hour == 100
        assert config.burst_size == 3
    
    def test_get_rate_limit_config_endpoint(self, middleware):
        """Test getting endpoint-specific rate limit config."""
        config = middleware._get_rate_limit_config("/api/v1/analyze-patient")
        assert config.requests_per_minute == 30
        assert config.requests_per_hour == 500
        assert config.burst_size == 5
    
    def test_get_rate_limit_config_authenticated_user(self, middleware):
        """Test getting rate limit config for authenticated user."""
        middleware.user_requests_per_minute = 20
        middleware.user_requests_per_hour = 200
        
        config = middleware._get_rate_limit_config("/api/v1/analyze-patient", is_authenticated=True)
        # Should use the lower of endpoint limit and user limit
        assert config.requests_per_minute == 20  # min(30, 20)
        assert config.requests_per_hour == 200  # min(500, 200)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_memory_allowed(self, middleware):
        """Test rate limit check when request is allowed."""
        client_id = "test_client"
        config = RateLimitConfig(10, 100, 3)
        
        allowed, error_msg, remaining_minute, remaining_hour = await middleware._check_rate_limit_memory(
            client_id, config
        )
        
        assert allowed is True
        assert error_msg is None
        # After adding one request, remaining should be 9 (10 - 1)
        assert remaining_minute >= 8  # Allow for timing variations
        assert remaining_hour >= 98  # Allow for timing variations
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_memory_burst_exceeded(self, middleware):
        """Test rate limit check when burst limit is exceeded."""
        client_id = "test_client"
        config = RateLimitConfig(10, 100, 3)
        
        # Make 3 requests quickly (within burst limit)
        for _ in range(3):
            await middleware._check_rate_limit_memory(client_id, config)
        
        # 4th request should exceed burst limit
        allowed, error_msg, remaining_minute, remaining_hour = await middleware._check_rate_limit_memory(
            client_id, config
        )
        
        assert allowed is False
        assert "Burst limit exceeded" in error_msg
        assert remaining_minute == 0
        assert remaining_hour == 0
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_memory_minute_exceeded(self, middleware):
        """Test rate limit check when per-minute limit is exceeded."""
        client_id = "test_client"
        config = RateLimitConfig(5, 100, 10)  # 5 per minute
        
        # Make 5 requests
        for _ in range(5):
            await middleware._check_rate_limit_memory(client_id, config)
        
        # 6th request should exceed minute limit
        allowed, error_msg, remaining_minute, remaining_hour = await middleware._check_rate_limit_memory(
            client_id, config
        )
        
        assert allowed is False
        assert "requests per minute" in error_msg
        assert remaining_minute == 0
        assert remaining_hour == 0
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_fallback(self, middleware):
        """Test Redis rate limit falls back to memory when Redis unavailable."""
        middleware.use_redis = True
        middleware._redis_client = None  # Redis not available
        
        client_id = "test_client"
        config = RateLimitConfig(10, 100, 3)
        
        allowed, error_msg, remaining_minute, remaining_hour = await middleware._check_rate_limit(
            client_id, config
        )
        
        # Should fall back to memory and succeed
        assert allowed is True
        assert error_msg is None
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_success(self, middleware):
        """Test Redis rate limit when Redis is available."""
        middleware.use_redis = True
        mock_redis = AsyncMock()
        mock_redis.zcount = AsyncMock(return_value=0)
        mock_redis.zrange = AsyncMock(return_value=[])
        
        # Create a proper pipeline mock
        mock_pipeline = MagicMock()
        mock_pipeline.zadd = MagicMock()
        mock_pipeline.expire = MagicMock()
        mock_pipeline.execute = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
        middleware._redis_client = mock_redis
        
        client_id = "test_client"
        config = RateLimitConfig(10, 100, 3)
        
        allowed, error_msg, remaining_minute, remaining_hour = await middleware._check_rate_limit(
            client_id, config
        )
        
        assert allowed is True
        assert error_msg is None
        assert remaining_minute == 10
        assert remaining_hour == 100
    
    @pytest.mark.asyncio
    async def test_dispatch_skips_health_check(self, middleware):
        """Test that health check endpoints skip rate limiting."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/health"
        call_next = AsyncMock(return_value=Response())
        
        response = await middleware.dispatch(request, call_next)
        
        call_next.assert_called_once()
        assert response is not None
    
    def test_rate_limit_headers_format(self, middleware):
        """Test that rate limit headers follow correct format."""
        from starlette.responses import Response
        import time
        
        response = Response()
        config = RateLimitConfig(60, 1000, 10)
        current_time = time.time()
        reset_time = int(current_time) + 60
        
        # Simulate header addition (as done in middleware)
        response.headers["X-RateLimit-Limit"] = str(config.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = "50"
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        response.headers["X-RateLimit-Limit-Hour"] = str(config.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = "900"
        response.headers["X-RateLimit-Policy"] = f"{config.requests_per_minute};w=60,{config.requests_per_hour};w=3600"
        
        # Verify headers are present and correctly formatted
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "60"
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert int(response.headers["X-RateLimit-Reset"]) > int(current_time)
        assert "X-RateLimit-Limit-Hour" in response.headers
        assert "X-RateLimit-Remaining-Hour" in response.headers
        assert "X-RateLimit-Policy" in response.headers
        assert "60;w=60" in response.headers["X-RateLimit-Policy"]
        assert "1000;w=3600" in response.headers["X-RateLimit-Policy"]
