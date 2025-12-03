"""
Pytest Configuration and Fixtures
Provides test environment setup, database fixtures, and mock integrations.
"""

import os
import sys
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import patch, MagicMock

# Set testing environment BEFORE importing app
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "test"

from backend.main import app


# ============================================================================
# Core Configuration
# ============================================================================

@pytest.fixture(scope="session")
def anyio_backend():
    """Restrict anyio tests to the asyncio backend."""
    yield "asyncio"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def dependency_overrides_guard():
    """Save and restore FastAPI dependency overrides for each test."""
    original_overrides = dict(app.dependency_overrides)
    try:
        yield app.dependency_overrides
    finally:
        app.dependency_overrides = original_overrides


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
async def test_db():
    """
    Provide a clean test database for each test.
    Uses in-memory SQLite for speed.
    """
    from backend.database.connection import init_database, get_db_session
    from backend.database.models import Base
    
    # Initialize test database
    await init_database()
    
    async with get_db_session() as session:
        yield session
        # Cleanup after test
        await session.rollback()


@pytest.fixture(scope="function")
def sync_test_db():
    """Synchronous database fixture for non-async tests."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.database.models import Base
    
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    engine.dispose()


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_redis():
    """Provide mock Redis client."""
    from tests.mocks.redis_client import MockRedisClient
    client = MockRedisClient()
    
    with patch("backend.database.connection.get_redis_client", return_value=client):
        yield client


@pytest.fixture
def mock_llm():
    """Provide mock LLM engine."""
    from tests.mocks.llm_engine import MockLLMEngine
    engine = MockLLMEngine()
    
    with patch("backend.llm_engine.LLMEngine", return_value=engine):
        yield engine


@pytest.fixture
def mock_fhir():
    """Provide mock FHIR server."""
    from tests.mocks.fhir_server import MockFHIRServer
    from tests.fixtures.fhir_bundles import create_patient_bundle
    
    server = MockFHIRServer()
    # Pre-populate with test data
    server.add_bundle(create_patient_bundle())
    
    yield server


@pytest.fixture
def auth_token():
    """Provide a valid test authentication token."""
    from tests.mocks.oauth_provider import create_test_user_token
    return create_test_user_token(
        user_id="test-user-123",
        email="test@example.com",
        roles=["user", "admin"]
    )


@pytest.fixture
def auth_headers(auth_token):
    """Provide authentication headers for API requests."""
    return {"Authorization": f"Bearer {auth_token}"}


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_patient():
    """Provide a sample patient for testing."""
    from tests.fixtures.patients import create_sample_patient
    return create_sample_patient()


@pytest.fixture
def high_risk_patient():
    """Provide a high-risk patient for testing alerts."""
    from tests.fixtures.patients import create_high_risk_patient
    return create_high_risk_patient()


@pytest.fixture
def sample_conditions():
    """Provide sample medical conditions."""
    from tests.fixtures.conditions import ConditionFactory
    return ConditionFactory.create_batch(3)


@pytest.fixture
def sample_medications():
    """Provide sample medications."""
    from tests.fixtures.medications import MedicationFactory
    return MedicationFactory.create_batch(5)


@pytest.fixture
def sample_alerts():
    """Provide sample alerts."""
    from tests.fixtures.alerts import AlertFactory
    return AlertFactory.create_batch(3)


@pytest.fixture
def fhir_bundle():
    """Provide a complete FHIR bundle."""
    from tests.fixtures.fhir_bundles import create_patient_bundle
    return create_patient_bundle()


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Provide TestClient for API testing."""
    from fastapi.testclient import TestClient
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client():
    """Provide async client for async tests."""
    from httpx import AsyncClient, ASGITransport
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# ============================================================================
# Utility Functions
# ============================================================================

def is_ci_environment() -> bool:
    """Check if running in CI environment."""
    return os.environ.get("CI", "false").lower() == "true"


def is_testing() -> bool:
    """Check if in testing mode."""
    return os.environ.get("TESTING", "false").lower() == "true"


def skip_if_no_redis():
    """Skip test if Redis is not available."""
    return pytest.mark.skipif(
        is_ci_environment() or os.environ.get("SKIP_REDIS", "false").lower() == "true",
        reason="Redis not available in this environment"
    )


def skip_if_no_fhir():
    """Skip test if FHIR server is not available."""
    return pytest.mark.skipif(
        is_ci_environment() or os.environ.get("SKIP_FHIR", "false").lower() == "true",
        reason="FHIR server not available in this environment"
    )


# ============================================================================
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test (no external deps)")
    config.addinivalue_line("markers", "integration: mark test as integration test (needs DB)")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test (needs all services)")
    config.addinivalue_line("markers", "slow: mark test as slow-running")
    config.addinivalue_line("markers", "requires_redis: test requires Redis")
    config.addinivalue_line("markers", "requires_fhir: test requires FHIR server")

