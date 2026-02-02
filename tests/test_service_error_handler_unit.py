import pytest
from backend.utils.service_error_handler import ServiceErrorHandler
from fastapi import HTTPException, Request
from unittest.mock import MagicMock

def test_safe_execution_success():
    """Verify code runs normally when no exception is raised."""
    executed = False
    with ServiceErrorHandler.safe_execution({"op": "test"}):
        executed = True
    assert executed

def test_safe_execution_http_exception_reraised():
    """Verify HTTPExceptions are re-raised as-is."""
    with pytest.raises(HTTPException) as exc:
        with ServiceErrorHandler.safe_execution({"op": "test"}):
            raise HTTPException(status_code=404, detail="Not Found")
    assert exc.value.status_code == 404

def test_safe_execution_generic_exception_handled():
    """Verify generic exceptions are converted to HTTPException."""
    # Mock handle_service_error to avoid logging side effects and full dependency
    original_handler = ServiceErrorHandler.handle_service_error
    ServiceErrorHandler.handle_service_error = MagicMock(return_value=HTTPException(status_code=500, detail="Handled"))
    
    try:
        with pytest.raises(HTTPException) as exc:
            with ServiceErrorHandler.safe_execution({"op": "test"}):
                raise ValueError("Boom")
        assert exc.value.status_code == 500
        assert exc.value.detail == "Handled"
        ServiceErrorHandler.handle_service_error.assert_called_once()
    finally:
        ServiceErrorHandler.handle_service_error = original_handler
