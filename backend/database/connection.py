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
    # Convert Windows backslashes to forward slashes for URL compatibility
    db_path_str = str(db_path).replace("\\", "/")
    return f"sqlite+aiosqlite:///{db_path_str}"


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
    
    # Configure connection arguments based on database type
    connect_args = {}
    if "sqlite" in db_url.lower():
        # SQLite-specific connection arguments
        connect_args = {
            "timeout": 10,  # Connection timeout in seconds
            "check_same_thread": False,  # For async SQLite compatibility
        }
    else:
        # PostgreSQL/other database connection arguments
        connect_args = {
            "connect_timeout": 10,
            "command_timeout": 30,
        }
    
    _engine = create_async_engine(
        db_url,
        echo=os.getenv("DEBUG", "False").lower() == "true",
        pool_pre_ping=True,  # Verify connections before using
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,  # Recycle connections after 1 hour
        connect_args=connect_args,
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
    
    # Run Alembic migrations to ensure database schema is up to date
    # This ensures Alembic knows about the database state and prevents
    # "Target database is not up to date" errors when autogenerating migrations
    try:
        from alembic.config import Config
        from alembic import script
        from alembic import command
        
        # Get sync engine for Alembic (Alembic doesn't support async directly)
        db_url_sync = db_url
        if db_url_sync.startswith("sqlite+aiosqlite:///"):
            db_url_sync = db_url_sync.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
        elif db_url_sync.startswith("postgresql+asyncpg://"):
            db_url_sync = db_url_sync.replace("postgresql+asyncpg://", "postgresql://", 1)
        
        # Create Alembic config
        import pathlib
        project_root = pathlib.Path(__file__).parent.parent.parent
        alembic_cfg = Config(str(project_root / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url_sync)
        
        # Check if alembic_version table exists
        from sqlalchemy import create_engine, inspect, text
        sync_engine = create_engine(db_url_sync)
        
        with sync_engine.connect() as conn:
            inspector = inspect(sync_engine)
            tables = inspector.get_table_names()
            
            if "alembic_version" not in tables:
                # Database exists but Alembic hasn't been initialized
                # Check if we have existing tables that match our models
                expected_tables = ["analysis_history", "documents", "ocr_extractions", 
                                 "user_sessions", "audit_logs", "users"]
                has_existing_tables = any(table in tables for table in expected_tables)
                
                if has_existing_tables:
                    # Stamp database with current head revision
                    logger.info("Stamping database with current Alembic version...")
                    command.stamp(alembic_cfg, "head")
                    logger.info("✓ Database stamped with Alembic version")
                else:
                    # No existing tables, run migrations from scratch
                    logger.info("Running Alembic migrations...")
                    command.upgrade(alembic_cfg, "head")
                    logger.info("✓ Database migrations applied")
            else:
                # Alembic is initialized, check if we need to upgrade
                with conn.begin():
                    result = conn.execute(text("SELECT version_num FROM alembic_version"))
                    current_version = result.scalar()
                    logger.info(f"Current Alembic version: {current_version}")
                    
                    # Get head revision
                    script_dir = script.ScriptDirectory.from_config(alembic_cfg)
                    head_revision = script_dir.get_current_head()
                    
                    if current_version != head_revision:
                        logger.info(f"Upgrading database from {current_version} to {head_revision}...")
                        command.upgrade(alembic_cfg, "head")
                        logger.info("✓ Database upgraded to latest version")
                    else:
                        logger.info("✓ Database is up to date")
        
        sync_engine.dispose()
        
    except Exception as e:
        logger.warning(f"Failed to run Alembic migrations: {e}. Falling back to create_all().")
        # Fallback to create_all if Alembic fails
        from .models import Base
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.warning("✓ Database tables created using create_all() (Alembic not available)")
    
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

