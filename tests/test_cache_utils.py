"""
Tests for cache utility functions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.utils.cache_utils import (
    CacheMetrics,
    get_cache_metrics,
    batch_invalidate_cache,
    warm_cache,
    should_invalidate_cache,
)
from datetime import datetime, timezone, timedelta


class TestCacheMetrics:
    """Test cache metrics tracking."""
    
    def test_initial_state(self):
        """Test initial cache metrics state."""
        metrics = CacheMetrics()
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.operations == 0
        assert metrics.get_hit_rate() == 0.0
    
    def test_record_hit(self):
        """Test recording cache hits."""
        metrics = CacheMetrics()
        metrics.record_hit()
        assert metrics.hits == 1
        assert metrics.misses == 0
        assert metrics.operations == 1
        assert metrics.get_hit_rate() == 100.0
    
    def test_record_miss(self):
        """Test recording cache misses."""
        metrics = CacheMetrics()
        metrics.record_miss()
        assert metrics.hits == 0
        assert metrics.misses == 1
        assert metrics.operations == 1
        assert metrics.get_hit_rate() == 0.0
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        metrics = CacheMetrics()
        metrics.record_hit()
        metrics.record_hit()
        metrics.record_miss()
        assert metrics.hits == 2
        assert metrics.misses == 1
        assert metrics.operations == 3
        assert metrics.get_hit_rate() == pytest.approx(66.67, abs=0.01)
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        metrics = CacheMetrics()
        metrics.record_hit()
        metrics.record_miss()
        stats = metrics.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["operations"] == 2
        assert stats["hit_rate"] == 50.0
    
    def test_reset(self):
        """Test resetting metrics."""
        metrics = CacheMetrics()
        metrics.record_hit()
        metrics.record_miss()
        metrics.reset()
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.operations == 0


class TestBatchInvalidateCache:
    """Test batch cache invalidation."""
    
    @pytest.mark.asyncio
    async def test_batch_invalidate_success(self):
        """Test successful batch cache invalidation."""
        redis_client = AsyncMock()
        redis_client.keys = AsyncMock(side_effect=[
            ["key1", "key2"],
            ["key3"],
        ])
        redis_client.delete = AsyncMock(side_effect=[2, 1])
        
        patterns = ["pattern1:*", "pattern2:*"]
        deleted = await batch_invalidate_cache(redis_client, patterns)
        
        assert deleted == 3
        assert redis_client.keys.call_count == 2
        assert redis_client.delete.call_count == 2
    
    @pytest.mark.asyncio
    async def test_batch_invalidate_no_redis(self):
        """Test batch invalidation with no Redis client."""
        deleted = await batch_invalidate_cache(None, ["pattern:*"])
        assert deleted == 0
    
    @pytest.mark.asyncio
    async def test_batch_invalidate_error_handling(self):
        """Test error handling during batch invalidation."""
        redis_client = AsyncMock()
        redis_client.keys = AsyncMock(side_effect=Exception("Redis error"))
        
        patterns = ["pattern:*"]
        deleted = await batch_invalidate_cache(redis_client, patterns)
        
        assert deleted == 0


class TestWarmCache:
    """Test cache warming."""
    
    @pytest.mark.asyncio
    async def test_warm_cache_success(self):
        """Test successful cache warming."""
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=None)  # Not cached
        redis_client.setex = AsyncMock()
        
        async def loader(key: str):
            return {"data": f"value_for_{key}"}
        
        cache_keys = ["key1", "key2"]
        warmed = await warm_cache(redis_client, cache_keys, loader, ttl=300)
        
        assert warmed == 2
        assert redis_client.setex.call_count == 2
    
    @pytest.mark.asyncio
    async def test_warm_cache_already_cached(self):
        """Test cache warming when keys are already cached."""
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=b'{"cached": "data"}')
        
        async def loader(key: str):
            return {"data": f"value_for_{key}"}
        
        cache_keys = ["key1"]
        warmed = await warm_cache(redis_client, cache_keys, loader, ttl=300)
        
        assert warmed == 0
        redis_client.setex.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_warm_cache_no_redis(self):
        """Test cache warming with no Redis client."""
        async def loader(key: str):
            return {"data": "value"}
        
        warmed = await warm_cache(None, ["key1"], loader, ttl=300)
        assert warmed == 0
    
    @pytest.mark.asyncio
    async def test_warm_cache_loader_error(self):
        """Test cache warming with loader errors."""
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=None)
        
        async def loader(key: str):
            raise Exception("Loader error")
        
        cache_keys = ["key1"]
        warmed = await warm_cache(redis_client, cache_keys, loader, ttl=300)
        
        assert warmed == 0


class TestShouldInvalidateCache:
    """Test cache invalidation decision logic."""
    
    def test_should_invalidate_old_cache(self):
        """Test that old cache should be invalidated."""
        old_time = datetime.now(timezone.utc) - timedelta(seconds=400)
        assert should_invalidate_cache(old_time, cache_ttl=300) is True
    
    def test_should_not_invalidate_fresh_cache(self):
        """Test that fresh cache should not be invalidated."""
        fresh_time = datetime.now(timezone.utc) - timedelta(seconds=100)
        assert should_invalidate_cache(fresh_time, cache_ttl=300) is False
    
    def test_should_invalidate_none(self):
        """Test that None timestamp should be invalidated."""
        assert should_invalidate_cache(None) is True
    
    def test_custom_threshold(self):
        """Test custom invalidation threshold."""
        # At 50% threshold, 200 seconds old cache with 300s TTL should be invalidated
        old_time = datetime.now(timezone.utc) - timedelta(seconds=200)
        assert should_invalidate_cache(old_time, cache_ttl=300, invalidation_threshold=0.5) is True
        
        # At 80% threshold, 200 seconds old cache should not be invalidated
        assert should_invalidate_cache(old_time, cache_ttl=300, invalidation_threshold=0.8) is False


class TestGetCacheMetrics:
    """Test global cache metrics instance."""
    
    def test_get_cache_metrics_returns_singleton(self):
        """Test that get_cache_metrics returns the same instance."""
        metrics1 = get_cache_metrics()
        metrics2 = get_cache_metrics()
        assert metrics1 is metrics2
