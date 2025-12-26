"""
Database connection management for PostgreSQL and Redis.
"""

import os
import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_redis_client: Optional[redis.Redis] = None


def get_database_url() -> str:
    """Get database URL from environment or use default."""
    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        # Convert postgresql:// to postgresql+asyncpg:// for async
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return db_url
    
    # Default to SQLite for development (fallback)
    # Use absolute path to avoid issues
    import pathlib
    db_path = pathlib.Path(__file__).parent.parent.parent / "healthcare_ai.db"
    return f"sqlite+aiosqlite:///{db_path}"


def get_redis_url() -> str:
    """Get Redis URL from environment or use default."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis_url


async def init_database() -> None:
    """Initialize database connections."""
    global _engine, _session_factory, _redis_client
    
    # Initialize PostgreSQL
    db_url = get_database_url()
    logger.info(f"Initializing database connection: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    
    _engine = create_async_engine(
        db_url,
        echo=os.getenv("DEBUG", "False").lower() == "true",
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Initialize Redis
    redis_url = get_redis_url()
    logger.info(f"Initializing Redis connection: {redis_url}")
    
    try:
        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await _redis_client.ping()
        logger.info("✓ Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Continuing without Redis cache.")
        _redis_client = None
    
    # Create tables (imported from models to avoid circular import)
    from .models import Base
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("✓ Database initialized successfully")


async def close_database() -> None:
    """Close database connections."""
    global _engine, _redis_client
    
    if _engine:
        await _engine.dispose()
        logger.info("Database connection closed")
    
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session context manager."""
    if not _session_factory:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client instance."""
    return _redis_client

