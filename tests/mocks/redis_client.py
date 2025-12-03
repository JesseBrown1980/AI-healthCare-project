"""
Mock Redis Client
Provides an in-memory Redis replacement for testing.
"""

from typing import Optional, Dict, Any, List, Union
from contextlib import contextmanager
from unittest.mock import patch, MagicMock
import json
import time
import asyncio


class MockRedisClient:
    """
    In-memory Redis mock that implements common Redis operations.
    
    Usage:
        redis = MockRedisClient()
        await redis.set("key", "value")
        value = await redis.get("key")
    """
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._connected = True
    
    async def ping(self) -> bool:
        """Check if connected."""
        return self._connected
    
    async def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        self._check_expiry(key)
        value = self._data.get(key)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value
    
    async def set(
        self,
        key: str,
        value: Union[str, bytes],
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> Optional[bool]:
        """Set a key-value pair."""
        if nx and key in self._data:
            return None
        if xx and key not in self._data:
            return None
        
        if isinstance(value, bytes):
            self._data[key] = value.decode("utf-8")
        else:
            self._data[key] = value
        
        if ex:
            self._expiry[key] = time.time() + ex
        elif px:
            self._expiry[key] = time.time() + (px / 1000)
        
        return True
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                self._expiry.pop(key, None)
                count += 1
        return count
    
    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        count = 0
        for key in keys:
            self._check_expiry(key)
            if key in self._data:
                count += 1
        return count
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on a key."""
        if key not in self._data:
            return False
        self._expiry[key] = time.time() + seconds
        return True
    
    async def ttl(self, key: str) -> int:
        """Get TTL of a key."""
        if key not in self._data:
            return -2
        if key not in self._expiry:
            return -1
        remaining = int(self._expiry[key] - time.time())
        return max(remaining, -2)
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        # Simple pattern matching (only supports * wildcard)
        if pattern == "*":
            return list(self._data.keys())
        
        import fnmatch
        return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
    
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get a hash field."""
        hash_data = self._data.get(name, {})
        if isinstance(hash_data, dict):
            return hash_data.get(key)
        return None
    
    async def hset(self, name: str, key: str = None, value: str = None, mapping: Dict = None) -> int:
        """Set hash field(s)."""
        if name not in self._data:
            self._data[name] = {}
        
        count = 0
        if key is not None and value is not None:
            if key not in self._data[name]:
                count = 1
            self._data[name][key] = value
        
        if mapping:
            for k, v in mapping.items():
                if k not in self._data[name]:
                    count += 1
                self._data[name][k] = v
        
        return count
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields."""
        return self._data.get(name, {})
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        if name not in self._data:
            return 0
        count = 0
        for key in keys:
            if key in self._data[name]:
                del self._data[name][key]
                count += 1
        return count
    
    async def incr(self, key: str) -> int:
        """Increment a key."""
        value = int(self._data.get(key, 0))
        value += 1
        self._data[key] = str(value)
        return value
    
    async def decr(self, key: str) -> int:
        """Decrement a key."""
        value = int(self._data.get(key, 0))
        value -= 1
        self._data[key] = str(value)
        return value
    
    async def lpush(self, key: str, *values: str) -> int:
        """Push to list (left)."""
        if key not in self._data:
            self._data[key] = []
        for value in reversed(values):
            self._data[key].insert(0, value)
        return len(self._data[key])
    
    async def rpush(self, key: str, *values: str) -> int:
        """Push to list (right)."""
        if key not in self._data:
            self._data[key] = []
        for value in values:
            self._data[key].append(value)
        return len(self._data[key])
    
    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        """Get list range."""
        if key not in self._data:
            return []
        if stop == -1:
            return self._data[key][start:]
        return self._data[key][start:stop + 1]
    
    async def flushall(self) -> bool:
        """Clear all data."""
        self._data = {}
        self._expiry = {}
        return True
    
    async def close(self):
        """Close connection (no-op for mock)."""
        self._connected = False
    
    def _check_expiry(self, key: str):
        """Check and remove expired keys."""
        if key in self._expiry:
            if time.time() > self._expiry[key]:
                self._data.pop(key, None)
                self._expiry.pop(key, None)
    
    # Sync versions for compatibility
    def get_sync(self, key: str) -> Optional[str]:
        return asyncio.get_event_loop().run_until_complete(self.get(key))
    
    def set_sync(self, key: str, value: str, **kwargs) -> bool:
        return asyncio.get_event_loop().run_until_complete(self.set(key, value, **kwargs))


@contextmanager
def mock_redis():
    """
    Context manager to mock Redis client.
    
    Usage:
        with mock_redis() as redis:
            await redis.set("key", "value")
            # Your code that uses Redis will use this mock
    """
    mock_client = MockRedisClient()
    
    with patch("backend.database.connection.get_redis_client", return_value=mock_client):
        with patch("redis.asyncio.Redis", return_value=mock_client):
            with patch("redis.Redis", return_value=mock_client):
                yield mock_client
