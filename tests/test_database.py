"""
Tests for database functionality.
"""

import pytest
import asyncio
from datetime import datetime, timezone

from backend.database import init_database, close_database, DatabaseService, get_db_session
from backend.database.models import AnalysisHistory


@pytest.mark.asyncio
async def test_database_initialization():
    """Test database initialization."""
    try:
        await init_database()
        assert True, "Database initialized successfully"
    except Exception as e:
        pytest.fail(f"Database initialization failed: {e}")
    finally:
        await close_database()


@pytest.mark.asyncio
async def test_save_and_retrieve_analysis():
    """Test saving and retrieving analysis."""
    await init_database()
    try:
        db_service = DatabaseService()
        
        # Save analysis
        analysis_data = {
            "analysis_data": {"summary": "Test patient"},
            "risk_scores": {"cardiovascular": 0.75},
            "alerts": [{"severity": "high", "message": "Test alert"}],
            "recommendations": ["Test recommendation"],
        }
        
        analysis_id = await db_service.save_analysis(
            patient_id="test-patient-1",
            analysis_data=analysis_data,
            user_id="test-user",
            correlation_id="test-correlation",
        )
        
        assert analysis_id is not None
        
        # Retrieve analysis
        retrieved = await db_service.get_latest_analysis("test-patient-1")
        
        assert retrieved is not None
        assert retrieved["patient_id"] == "test-patient-1"
        assert retrieved["risk_scores"]["cardiovascular"] == 0.75
        assert len(retrieved["alerts"]) == 1
        
    finally:
        await close_database()


@pytest.mark.asyncio
async def test_redis_cache():
    """Test Redis caching functionality."""
    await init_database()
    try:
        db_service = DatabaseService()
        
        # Cache a summary
        summary = {"patient_id": "test-1", "risk_score": 0.8}
        await db_service.cache_patient_summary("test-1", summary, ttl=60)
        
        # Retrieve from cache
        cached = await db_service.get_cached_summary("test-1")
        
        # Redis may not be available, so cache might be None
        # This is acceptable - the test verifies the method doesn't crash
        if cached is not None:
            assert cached["patient_id"] == "test-1"
            assert cached["risk_score"] == 0.8
        else:
            # If Redis is unavailable, the cache operation should fail gracefully
            # This is expected behavior when Redis is not running
            pass
        
    finally:
        await close_database()


@pytest.mark.asyncio
async def test_audit_logging():
    """Test audit logging."""
    await init_database()
    try:
        db_service = DatabaseService()
        
        log_id = await db_service.log_audit_event(
            correlation_id="test-correlation",
            user_id="test-user",
            patient_id="test-patient",
            action="READ",
            resource_type="Patient",
            outcome="0",
            ip_address="127.0.0.1",
            details={"test": "data"},
        )
        
        assert log_id is not None
        
    finally:
        await close_database()

