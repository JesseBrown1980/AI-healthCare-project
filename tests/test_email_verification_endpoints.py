"""
Tests for email verification API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from backend.main import app
from backend.di import get_database_service


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def dependency_overrides_guard():
    """Save and restore FastAPI dependency overrides for each test."""
    original_overrides = dict(app.dependency_overrides)
    try:
        yield app.dependency_overrides
    finally:
        app.dependency_overrides = original_overrides


def test_verify_email_request_success(client, dependency_overrides_guard):
    """Test successful email verification token generation."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'generate_verification_token', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "test-verification-token-123"
        
        response = client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": "test@example.com",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "token" in data["message"].lower() or "generated" in data["message"].lower()


def test_verify_email_request_user_not_found(client, dependency_overrides_guard):
    """Test email verification request for non-existent user (should still return success)."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'generate_verification_token', new_callable=AsyncMock) as mock_generate:
        # Return None if user doesn't exist (don't reveal user existence)
        mock_generate.return_value = None
        
        response = client.post(
            "/api/v1/auth/verify-email",
            json={
                "email": "nonexistent@example.com",
            },
        )
        
        # Should still return success to prevent email enumeration
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


def test_verify_email_request_no_database(client, dependency_overrides_guard):
    """Test email verification request when database service is unavailable."""
    app.dependency_overrides[get_database_service] = lambda: None
    
    response = client.post(
        "/api/v1/auth/verify-email",
        json={
            "email": "test@example.com",
        },
    )
    
    assert response.status_code == 503
    error_msg = response.json().get("message", response.json().get("detail", ""))
    assert "database" in error_msg.lower() or "service" in error_msg.lower()


def test_verify_email_request_invalid_email(client, dependency_overrides_guard):
    """Test email verification request with invalid email format."""
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    response = client.post(
        "/api/v1/auth/verify-email",
        json={
            "email": "invalid-email",
        },
    )
    
    # FastAPI validation should return 422
    assert response.status_code == 422


def test_verify_email_confirm_success(client, dependency_overrides_guard):
    """Test successful email verification confirmation."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'verify_email_with_token', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = True
        
        response = client.post(
            "/api/v1/auth/verify-email/confirm",
            json={
                "email": "test@example.com",
                "token": "valid-verification-token-123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "verified" in data["message"].lower() or "success" in data["message"].lower()


def test_verify_email_confirm_invalid_token(client, dependency_overrides_guard):
    """Test email verification confirmation with invalid token."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'verify_email_with_token', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = False
        
        response = client.post(
            "/api/v1/auth/verify-email/confirm",
            json={
                "email": "test@example.com",
                "token": "invalid-token",
            },
        )
        
        assert response.status_code == 400
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "invalid" in error_msg.lower() or "expired" in error_msg.lower() or "token" in error_msg.lower()


def test_verify_email_confirm_no_database(client, dependency_overrides_guard):
    """Test email verification confirmation when database service is unavailable."""
    app.dependency_overrides[get_database_service] = lambda: None
    
    response = client.post(
        "/api/v1/auth/verify-email/confirm",
        json={
            "email": "test@example.com",
            "token": "test-token",
        },
    )
    
    assert response.status_code == 503
    error_msg = response.json().get("message", response.json().get("detail", ""))
    assert "database" in error_msg.lower() or "service" in error_msg.lower()


def test_verify_email_confirm_invalid_email_format(client, dependency_overrides_guard):
    """Test email verification confirmation with invalid email format."""
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    response = client.post(
        "/api/v1/auth/verify-email/confirm",
        json={
            "email": "invalid-email",
            "token": "test-token",
        },
    )
    
    # FastAPI validation should return 422
    assert response.status_code == 422


def test_verify_email_confirm_missing_token(client, dependency_overrides_guard):
    """Test email verification confirmation with missing token."""
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    response = client.post(
        "/api/v1/auth/verify-email/confirm",
        json={
            "email": "test@example.com",
        },
    )
    
    # FastAPI validation should return 422 for missing required field
    assert response.status_code == 422
