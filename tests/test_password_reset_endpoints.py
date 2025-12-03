"""
Tests for password reset API endpoints.
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


def test_password_reset_request_success(client, dependency_overrides_guard):
    """Test successful password reset token generation."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'generate_password_reset_token', new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "test-reset-token-123"
        
        response = client.post(
            "/api/v1/auth/password-reset",
            json={
                "email": "test@example.com",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "token" in data["message"].lower() or "generated" in data["message"].lower()


def test_password_reset_request_user_not_found(client, dependency_overrides_guard):
    """Test password reset request for non-existent user (should still return success)."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'generate_password_reset_token', new_callable=AsyncMock) as mock_generate:
        # Return None if user doesn't exist (don't reveal user existence)
        mock_generate.return_value = None
        
        response = client.post(
            "/api/v1/auth/password-reset",
            json={
                "email": "nonexistent@example.com",
            },
        )
        
        # Should still return success to prevent email enumeration
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


def test_password_reset_request_no_database(client, dependency_overrides_guard):
    """Test password reset request when database service is unavailable."""
    app.dependency_overrides[get_database_service] = lambda: None
    
    response = client.post(
        "/api/v1/auth/password-reset",
        json={
            "email": "test@example.com",
        },
    )
    
    assert response.status_code == 503
    error_msg = response.json().get("message", response.json().get("detail", ""))
    assert "database" in error_msg.lower() or "service" in error_msg.lower()


def test_password_reset_request_invalid_email(client, dependency_overrides_guard):
    """Test password reset request with invalid email format."""
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    response = client.post(
        "/api/v1/auth/password-reset",
        json={
            "email": "invalid-email",
        },
    )
    
    # FastAPI validation should return 422
    assert response.status_code == 422


def test_password_reset_confirm_success(client, dependency_overrides_guard):
    """Test successful password reset confirmation."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'verify_password_reset_token', new_callable=AsyncMock) as mock_verify, \
         patch.object(UserService, 'reset_password_with_token', new_callable=AsyncMock) as mock_reset:
        
        mock_verify.return_value = True
        mock_reset.return_value = True
        
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "test@example.com",
                "token": "valid-reset-token-123",
                "new_password": "NewStrongPass123!",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "success" in data["message"].lower() or "reset" in data["message"].lower()


def test_password_reset_confirm_invalid_token(client, dependency_overrides_guard):
    """Test password reset confirmation with invalid token."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'verify_password_reset_token', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = False
        
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "test@example.com",
                "token": "invalid-token",
                "new_password": "NewStrongPass123!",
            },
        )
        
        assert response.status_code == 400
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "invalid" in error_msg.lower() or "expired" in error_msg.lower() or "token" in error_msg.lower()


def test_password_reset_confirm_weak_password(client, dependency_overrides_guard):
    """Test password reset confirmation with weak password."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'verify_password_reset_token', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = True
        
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "test@example.com",
                "token": "valid-token",
                "new_password": "weak",
            },
        )
        
        # FastAPI may return 422 for validation or 400 for password strength check
        assert response.status_code in [400, 422]
        if response.status_code == 400:
            error_msg = response.json().get("message", response.json().get("detail", ""))
            assert "password" in error_msg.lower() or "strength" in error_msg.lower()


def test_password_reset_confirm_no_database(client, dependency_overrides_guard):
    """Test password reset confirmation when database service is unavailable."""
    app.dependency_overrides[get_database_service] = lambda: None
    
    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": "test@example.com",
            "token": "test-token",
            "new_password": "NewStrongPass123!",
        },
    )
    
    assert response.status_code == 503
    error_msg = response.json().get("message", response.json().get("detail", ""))
    assert "database" in error_msg.lower() or "service" in error_msg.lower()


def test_password_reset_confirm_reset_fails(client, dependency_overrides_guard):
    """Test password reset confirmation when reset operation fails."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'verify_password_reset_token', new_callable=AsyncMock) as mock_verify, \
         patch.object(UserService, 'reset_password_with_token', new_callable=AsyncMock) as mock_reset:
        
        mock_verify.return_value = True
        mock_reset.return_value = False  # Reset operation fails
        
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "test@example.com",
                "token": "valid-token",
                "new_password": "NewStrongPass123!",
            },
        )
        
        assert response.status_code == 400
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "failed" in error_msg.lower() or "invalid" in error_msg.lower() or "expired" in error_msg.lower()


def test_password_reset_confirm_invalid_email_format(client, dependency_overrides_guard):
    """Test password reset confirmation with invalid email format."""
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": "invalid-email",
            "token": "test-token",
            "new_password": "NewStrongPass123!",
        },
    )
    
    # FastAPI validation should return 422
    assert response.status_code == 422


def test_password_reset_confirm_password_too_short(client, dependency_overrides_guard):
    """Test password reset confirmation with password that's too short."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'verify_password_reset_token', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = True
        
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": "test@example.com",
                "token": "valid-token",
                "new_password": "short",  # Less than 8 characters
            },
        )
        
        # Should fail validation (422) or password strength check (400)
        assert response.status_code in [400, 422]
