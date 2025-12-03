"""
Performance optimization utilities for database queries and async operations.
"""

import time
import asyncio
import logging
from typing import List, Callable, Any, Optional, Dict, TypeVar, Awaitable
from functools import wraps
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

T = TypeVar('T')


class QueryOptimizer:
    """Utilities for optimizing database queries."""
    
    @staticmethod
    async def batch_fetch(
        fetch_func: Callable[[str], Awaitable[Any]],
        ids: List[str],
        batch_size: int = 50,
        max_concurrent: int = 10,
    ) -> Dict[str, Any]:
        """
        Batch fetch items with concurrency control.
        
        Args:
            fetch_func: Async function that takes an ID and returns data
            ids: List of IDs to fetch
            batch_size: Number of items to process in each batch
            max_concurrent: Maximum concurrent operations
            
        Returns:
            Dictionary mapping IDs to fetched data
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(id: str):
            async with semaphore:
                try:
                    return id, await fetch_func(id)
                except Exception as e:
                    logger.warning(f"Failed to fetch {id}: {e}")
                    return id, None
        
        # Process in batches
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            tasks = [fetch_with_semaphore(id) for id in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch fetch error: {result}")
                elif result:
                    id, data = result
                    if data is not None:
                        results[id] = data
        
        return results
    
    @staticmethod
    def optimize_query_params(
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        max_limit: int = 1000,
        default_limit: int = 100,
    ) -> tuple[int, int]:
        """
        Optimize query pagination parameters.
        
        Args:
            limit: Requested limit
            offset: Requested offset
            max_limit: Maximum allowed limit
            default_limit: Default limit if not specified
            
        Returns:
            Tuple of (optimized_limit, optimized_offset)
        """
        if limit is None:
            limit = default_limit
        elif limit > max_limit:
            limit = max_limit
        elif limit < 1:
            limit = default_limit
        
        if offset is None:
            offset = 0
        elif offset < 0:
            offset = 0
        
        return limit, offset


def async_timing_decorator(func: Callable) -> Callable:
    """
    Decorator to measure and log async function execution time.
    
    Usage:
        @async_timing_decorator
        async def my_function():
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Log slow operations
            if duration > 1.0:
                logger.warning(
                    f"Slow operation detected: {func.__name__} took {duration:.3f}s"
                )
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Operation {func.__name__} failed after {duration:.3f}s: {e}"
            )
            raise
    
    return wrapper


def sync_timing_decorator(func: Callable) -> Callable:
    """
    Decorator to measure and log sync function execution time.
    
    Usage:
        @sync_timing_decorator
        def my_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Log slow operations
            if duration > 1.0:
                logger.warning(
                    f"Slow operation detected: {func.__name__} took {duration:.3f}s"
                )
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Operation {func.__name__} failed after {duration:.3f}s: {e}"
            )
            raise
    
    return wrapper


class AsyncBatchProcessor:
    """Process items in batches with concurrency control."""
    
    def __init__(self, batch_size: int = 50, max_concurrent: int = 10):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of items per batch
            max_concurrent: Maximum concurrent operations
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
    
    async def process(
        self,
        items: List[Any],
        process_func: Callable[[Any], Awaitable[Any]],
    ) -> List[Any]:
        """
        Process items in batches.
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            
        Returns:
            List of processed results
        """
        results = []
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(item: Any):
            async with semaphore:
                try:
                    return await process_func(item)
                except Exception as e:
                    logger.warning(f"Failed to process item: {e}")
                    return None
        
        # Process in batches
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            tasks = [process_with_semaphore(item) for item in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
                elif result is not None:
                    results.append(result)
        
        return results


def optimize_connection_pool(
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_recycle: int = 3600,
    pool_pre_ping: bool = True,
) -> Dict[str, Any]:
    """
    Get optimized connection pool configuration.
    
    Args:
        pool_size: Base pool size
        max_overflow: Maximum overflow connections
        pool_recycle: Connection recycle time in seconds
        pool_pre_ping: Enable connection health checks
        
    Returns:
        Dictionary with pool configuration
    """
    return {
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_recycle": pool_recycle,
        "pool_pre_ping": pool_pre_ping,
    }
