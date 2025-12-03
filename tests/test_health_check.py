"""
Tests for enhanced health check endpoint.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.api.v1.endpoints.system import health_check
from backend.llm_engine import LLMEngine
from backend.rag_fusion import RAGFusion
from backend.s_lora_manager import SLoRAManager
from backend.mlc_learning import MLCLearning


@pytest.fixture
def mock_llm_engine():
    """Mock LLM engine."""
    return MagicMock(spec=LLMEngine)


@pytest.fixture
def mock_rag_fusion():
    """Mock RAG fusion."""
    return MagicMock(spec=RAGFusion)


@pytest.fixture
def mock_s_lora_manager():
    """Mock S-LoRA manager."""
    return MagicMock(spec=SLoRAManager)


@pytest.fixture
def mock_mlc_learning():
    """Mock MLC learning."""
    return MagicMock(spec=MLCLearning)


@pytest.fixture
def mock_request():
    """Mock FastAPI request."""
    request = MagicMock()
    return request


@pytest.mark.asyncio
async def test_health_check_all_healthy(
    mock_request, mock_llm_engine, mock_rag_fusion, mock_s_lora_manager, mock_mlc_learning
):
    """Test health check when all components are healthy."""
    with patch('backend.database.get_db_session') as mock_db, \
         patch('backend.database.connection.get_redis_client', return_value=MagicMock(ping=AsyncMock())), \
         patch.dict('os.environ', {'DEBUG': 'False'}):
        
        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = await health_check(
            request=mock_request,
            llm_engine=mock_llm_engine,
            rag_fusion=mock_rag_fusion,
            s_lora_manager=mock_s_lora_manager,
            mlc_learning=mock_mlc_learning,
        )
        
        assert response["status"] == "healthy"
        assert response["components"]["database"]["status"] == "healthy"
        assert response["components"]["database"]["available"] is True
        assert response["components"]["llm_engine"]["available"] is True
        assert response["components"]["rag_fusion"]["available"] is True
        assert "timestamp" in response


@pytest.mark.asyncio
async def test_health_check_database_unhealthy(mock_request, mock_llm_engine, mock_rag_fusion):
    """Test health check when database is unhealthy."""
    with patch('backend.database.get_db_session') as mock_db, \
         patch('backend.database.connection.get_redis_client', return_value=None), \
         patch.dict('os.environ', {'DEBUG': 'False'}):
        
        # Make database connection fail
        mock_db.side_effect = Exception("Database connection failed")
        
        response = await health_check(
            request=mock_request,
            llm_engine=mock_llm_engine,
            rag_fusion=mock_rag_fusion,
            s_lora_manager=None,
            mlc_learning=None,
        )
        
        assert response["status"] == "degraded"
        assert response["components"]["database"]["status"] == "unhealthy"
        assert response["components"]["database"]["available"] is False
        assert "error" in response["components"]["database"]


@pytest.mark.asyncio
async def test_health_check_redis_unavailable(mock_request, mock_llm_engine):
    """Test health check when Redis is unavailable."""
    with patch('backend.database.get_db_session') as mock_db, \
         patch('backend.database.connection.get_redis_client', return_value=None), \
         patch.dict('os.environ', {'DEBUG': 'False'}):
        
        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = await health_check(
            request=mock_request,
            llm_engine=mock_llm_engine,
            rag_fusion=None,
            s_lora_manager=None,
            mlc_learning=None,
        )
        
        assert response["components"]["redis"]["status"] == "disabled"
        assert response["components"]["redis"]["available"] is False
        # Redis is optional, so status might still be healthy or degraded
        assert response["status"] in ["healthy", "degraded"]


@pytest.mark.asyncio
async def test_health_check_redis_connection_failure(mock_request, mock_llm_engine):
    """Test health check when Redis connection fails."""
    with patch('backend.database.get_db_session') as mock_db, \
         patch('backend.database.connection.get_redis_client') as mock_redis, \
         patch.dict('os.environ', {'DEBUG': 'False'}):
        
        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Make Redis ping fail
        mock_redis_client = MagicMock()
        mock_redis_client.ping = AsyncMock(side_effect=Exception("Redis connection failed"))
        mock_redis.return_value = mock_redis_client
        
        response = await health_check(
            request=mock_request,
            llm_engine=mock_llm_engine,
            rag_fusion=None,
            s_lora_manager=None,
            mlc_learning=None,
        )
        
        assert response["components"]["redis"]["status"] == "unhealthy"
        assert response["components"]["redis"]["available"] is False


@pytest.mark.asyncio
async def test_health_check_missing_components(mock_request):
    """Test health check when key components are missing."""
    with patch('backend.database.get_db_session') as mock_db, \
         patch('backend.database.connection.get_redis_client', return_value=None), \
         patch.dict('os.environ', {'DEBUG': 'False'}):
        
        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = await health_check(
            request=mock_request,
            llm_engine=None,  # Missing LLM
            rag_fusion=None,  # Missing RAG
            s_lora_manager=None,
            mlc_learning=None,
        )
        
        assert response["status"] == "degraded"
        assert response["components"]["llm_engine"]["status"] == "disabled"
        assert response["components"]["llm_engine"]["available"] is False
        assert response["components"]["rag_fusion"]["status"] == "disabled"
        assert response["components"]["rag_fusion"]["available"] is False


@pytest.mark.asyncio
async def test_health_check_debug_mode_shows_errors(mock_request):
    """Test health check in debug mode shows detailed errors."""
    with patch('backend.database.get_db_session') as mock_db, \
         patch('backend.database.connection.get_redis_client', return_value=None), \
         patch.dict('os.environ', {'DEBUG': 'True'}):
        
        # Make database connection fail
        error_msg = "Database connection failed: Connection refused"
        mock_db.side_effect = Exception(error_msg)
        
        response = await health_check(
            request=mock_request,
            llm_engine=None,
            rag_fusion=None,
            s_lora_manager=None,
            mlc_learning=None,
        )
        
        assert response["components"]["database"]["status"] == "unhealthy"
        assert error_msg in response["components"]["database"]["error"]


@pytest.mark.asyncio
async def test_health_check_production_mode_hides_errors(mock_request):
    """Test health check in production mode hides detailed errors."""
    with patch('backend.database.get_db_session') as mock_db, \
         patch('backend.database.connection.get_redis_client', return_value=None), \
         patch.dict('os.environ', {'DEBUG': 'False'}):
        
        # Make database connection fail
        error_msg = "Database connection failed: Connection refused"
        mock_db.side_effect = Exception(error_msg)
        
        response = await health_check(
            request=mock_request,
            llm_engine=None,
            rag_fusion=None,
            s_lora_manager=None,
            mlc_learning=None,
        )
        
        assert response["components"]["database"]["status"] == "unhealthy"
        assert error_msg not in response["components"]["database"]["error"]
        assert "Database unavailable" in response["components"]["database"]["error"]


@pytest.mark.asyncio
async def test_health_check_all_components_status(mock_request, mock_llm_engine, mock_rag_fusion):
    """Test that all component statuses are included."""
    with patch('backend.database.get_db_session') as mock_db, \
         patch('backend.database.connection.get_redis_client', return_value=None), \
         patch.dict('os.environ', {'DEBUG': 'False'}):
        
        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = await health_check(
            request=mock_request,
            llm_engine=mock_llm_engine,
            rag_fusion=mock_rag_fusion,
            s_lora_manager=None,
            mlc_learning=None,
        )
        
        # Check all expected components are present
        assert "database" in response["components"]
        assert "redis" in response["components"]
        assert "llm_engine" in response["components"]
        assert "rag_fusion" in response["components"]
        assert "s_lora_manager" in response["components"]
        assert "mlc_learning" in response["components"]
        
        # Check each component has status and available fields
        for component_name, component_status in response["components"].items():
            assert "status" in component_status
            assert "available" in component_status

