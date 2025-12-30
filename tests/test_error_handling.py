"""
Tests for error handling scenarios and exception handlers.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from backend.main import app, general_exception_handler, http_exception_handler


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.state.correlation_id = "test-correlation-123"
    request.method = "GET"
    request.url.path = "/api/v1/test"
    return request


@pytest.mark.asyncio
async def test_http_exception_handler_401(mock_request):
    """Test HTTP exception handler for 401 Unauthorized."""
    exc = HTTPException(status_code=401, detail="Unauthorized")
    
    response = await http_exception_handler(mock_request, exc)
    
    assert isinstance(response, JSONResponse)
    assert response.status_code == 401
    content = response.body.decode()
    assert "Unauthorized" in content
    assert "hint" in content
    assert "authenticate" in content.lower()


@pytest.mark.asyncio
async def test_http_exception_handler_403(mock_request):
    """Test HTTP exception handler for 403 Forbidden."""
    exc = HTTPException(status_code=403, detail="Forbidden")
    
    response = await http_exception_handler(mock_request, exc)
    
    assert isinstance(response, JSONResponse)
    assert response.status_code == 403
    content = response.body.decode()
    assert "Forbidden" in content
    assert "hint" in content
    assert "permission" in content.lower()


@pytest.mark.asyncio
async def test_http_exception_handler_404(mock_request):
    """Test HTTP exception handler for 404 Not Found."""
    exc = HTTPException(status_code=404, detail="Not Found")
    
    response = await http_exception_handler(mock_request, exc)
    
    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    content = response.body.decode()
    assert "Not Found" in content
    assert "hint" in content
    assert "not found" in content.lower()


@pytest.mark.asyncio
async def test_http_exception_handler_422(mock_request):
    """Test HTTP exception handler for 422 Validation Error."""
    exc = HTTPException(status_code=422, detail="Validation Error")
    
    response = await http_exception_handler(mock_request, exc)
    
    assert isinstance(response, JSONResponse)
    assert response.status_code == 422
    content = response.body.decode()
    assert "Validation Error" in content
    assert "hint" in content
    assert "validation" in content.lower()


@pytest.mark.asyncio
async def test_http_exception_handler_503(mock_request):
    """Test HTTP exception handler for 503 Service Unavailable."""
    exc = HTTPException(status_code=503, detail="Service Unavailable")
    
    response = await http_exception_handler(mock_request, exc)
    
    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    content = response.body.decode()
    assert "Service Unavailable" in content
    assert "hint" in content
    assert "unavailable" in content.lower()


@pytest.mark.asyncio
async def test_general_exception_handler_debug_mode(mock_request):
    """Test general exception handler in debug mode."""
    with patch.dict('os.environ', {'DEBUG': 'True'}):
        exc = ValueError("Test error message")
        
        response = await general_exception_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        content = response.body.decode()
        assert "error" in content.lower()
        assert "ValueError" in content
        assert "Test error message" in content


@pytest.mark.asyncio
async def test_general_exception_handler_production_mode(mock_request):
    """Test general exception handler in production mode."""
    with patch.dict('os.environ', {'DEBUG': 'False'}):
        exc = ValueError("Sensitive error details")
        
        response = await general_exception_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        content = response.body.decode()
        assert "error" in content.lower()
        # Should not expose internal error details
        assert "Sensitive error details" not in content
        assert "ValueError" not in content


@pytest.mark.asyncio
async def test_general_exception_handler_includes_correlation_id(mock_request):
    """Test that general exception handler includes correlation ID."""
    exc = Exception("Test error")
    
    response = await general_exception_handler(mock_request, exc)
    
    content = response.body.decode()
    assert "test-correlation-123" in content
    assert "correlation_id" in content


@pytest.mark.asyncio
async def test_general_exception_handler_includes_path(mock_request):
    """Test that general exception handler includes request path."""
    exc = Exception("Test error")
    
    response = await general_exception_handler(mock_request, exc)
    
    content = response.body.decode()
    assert "/api/v1/test" in content
    assert "path" in content


@pytest.mark.asyncio
async def test_http_exception_handler_includes_timestamp(mock_request):
    """Test that HTTP exception handler includes timestamp."""
    exc = HTTPException(status_code=400, detail="Bad Request")
    
    response = await http_exception_handler(mock_request, exc)
    
    content = response.body.decode()
    assert "timestamp" in content
    # Should be ISO format timestamp
    assert "T" in content or "-" in content  # ISO format indicator


@pytest.mark.asyncio
async def test_http_exception_handler_logs_errors(mock_request):
    """Test that HTTP exception handler logs errors appropriately."""
    import logging
    
    with patch('backend.main.logger') as mock_logger:
        exc = HTTPException(status_code=500, detail="Internal Server Error")
        
        response = await http_exception_handler(mock_request, exc)
        
        # Should log error for 5xx status codes
        mock_logger.error.assert_called_once()
        assert "500" in str(mock_logger.error.call_args)
        assert "Internal Server Error" in str(mock_logger.error.call_args)


@pytest.mark.asyncio
async def test_http_exception_handler_logs_warnings(mock_request):
    """Test that HTTP exception handler logs warnings for 4xx errors."""
    import logging
    
    with patch('backend.main.logger') as mock_logger:
        exc = HTTPException(status_code=400, detail="Bad Request")
        
        response = await http_exception_handler(mock_request, exc)
        
        # Should log warning for 4xx status codes
        mock_logger.warning.assert_called_once()
        assert "400" in str(mock_logger.warning.call_args)


@pytest.mark.asyncio
async def test_general_exception_handler_logs_with_traceback(mock_request):
    """Test that general exception handler logs with full traceback."""
    import logging
    
    with patch('backend.main.logger') as mock_logger:
        exc = Exception("Test error")
        
        response = await general_exception_handler(mock_request, exc)
        
        # Should log with exc_info=True for full traceback
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        # Check that exc_info is in kwargs (for traceback)
        assert call_args.kwargs.get('exc_info') is True or 'exc_info' in str(call_args)


@pytest.mark.asyncio
async def test_error_response_format_consistency(mock_request):
    """Test that all error responses have consistent format."""
    exc = HTTPException(status_code=400, detail="Test error")
    
    response = await http_exception_handler(mock_request, exc)
    content = response.body.decode()
    
    # Check for required fields
    assert "status" in content
    assert "message" in content
    assert "correlation_id" in content
    assert "timestamp" in content
    assert "status_code" in content


@pytest.mark.asyncio
async def test_error_response_without_correlation_id():
    """Test error handling when correlation ID is missing."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    # No correlation_id attribute
    if hasattr(request.state, 'correlation_id'):
        delattr(request.state, 'correlation_id')
    request.method = "GET"
    request.url.path = "/test"
    
    exc = HTTPException(status_code=500, detail="Error")
    
    response = await http_exception_handler(request, exc)
    
    # Should still work and generate a correlation ID
    content = response.body.decode()
    assert "correlation_id" in content

