"""
Cache utility functions for improved caching strategies.

Provides cache warming, batch invalidation, and cache hit rate monitoring.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CacheMetrics:
    """Track cache hit/miss rates for monitoring."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.operations = 0
    
    def record_hit(self):
        """Record a cache hit."""
        self.hits += 1
        self.operations += 1
    
    def record_miss(self):
        """Record a cache miss."""
        self.misses += 1
        self.operations += 1
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate as percentage."""
        if self.operations == 0:
            return 0.0
        return (self.hits / self.operations) * 100.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "operations": self.operations,
            "hit_rate": self.get_hit_rate(),
        }
    
    def reset(self):
        """Reset metrics."""
        self.hits = 0
        self.misses = 0
        self.operations = 0


# Global cache metrics instance
_cache_metrics = CacheMetrics()


def get_cache_metrics() -> CacheMetrics:
    """Get global cache metrics instance."""
    return _cache_metrics


async def batch_invalidate_cache(
    redis_client,
    patterns: List[str],
) -> int:
    """
    Batch invalidate cache entries matching multiple patterns.
    
    Args:
        redis_client: Redis client instance
        patterns: List of cache key patterns to invalidate
        
    Returns:
        Number of keys deleted
    """
    if not redis_client:
        return 0
    
    total_deleted = 0
    for pattern in patterns:
        try:
            keys = await redis_client.keys(pattern)
            if keys:
                deleted = await redis_client.delete(*keys)
                total_deleted += deleted
        except Exception as e:
            logger.warning(f"Failed to invalidate cache pattern {pattern}: {e}")
    
    return total_deleted


async def warm_cache(
    redis_client,
    cache_keys: List[str],
    loader_func,
    ttl: int = 300,
) -> int:
    """
    Warm cache by pre-loading frequently accessed data.
    
    Args:
        redis_client: Redis client instance
        cache_keys: List of cache keys to warm
        loader_func: Async function that takes a key and returns data to cache
        ttl: Time to live in seconds
        
    Returns:
        Number of keys successfully warmed
    """
    if not redis_client:
        return 0
    
    warmed = 0
    for key in cache_keys:
        try:
            # Check if already cached
            existing = await redis_client.get(key)
            if existing:
                continue
            
            # Load and cache
            data = await loader_func(key)
            if data:
                import json
                await redis_client.setex(
                    key,
                    ttl,
                    json.dumps(data, default=str),
                )
                warmed += 1
        except Exception as e:
            logger.warning(f"Failed to warm cache for key {key}: {e}")
    
    return warmed


def should_invalidate_cache(
    last_update: datetime,
    cache_ttl: int = 300,
    invalidation_threshold: float = 0.8,
) -> bool:
    """
    Determine if cache should be invalidated based on age.
    
    Args:
        last_update: Timestamp of last cache update
        cache_ttl: Cache time to live in seconds
        invalidation_threshold: Fraction of TTL after which to invalidate
        
    Returns:
        True if cache should be invalidated
    """
    if not last_update:
        return True
    
    age_seconds = (datetime.now(timezone.utc) - last_update).total_seconds()
    threshold = cache_ttl * invalidation_threshold
    
    return age_seconds > threshold
