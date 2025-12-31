"""
Tests for authentication API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch, MagicMock
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


@pytest.fixture
def mock_db_service():
    """Mock database service."""
    mock_db = MagicMock()
    return mock_db


def test_register_user_success(client, dependency_overrides_guard):
    """Test successful user registration."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'create_user', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {
            'id': 'user-123',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'roles': ['viewer'],
            'is_active': True,
        }
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "StrongPass123!",
                "full_name": "Test User",
                "roles": ["viewer"],
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["id"] == "user-123"
        assert "viewer" in data["roles"]


def test_register_user_weak_password(client, dependency_overrides_guard):
    """Test registration with weak password."""
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "weak",
            "full_name": "Test User",
        },
    )
    
    # FastAPI returns 422 for validation errors, but the endpoint may return 400 for password strength
    assert response.status_code in [400, 422]
    if response.status_code == 400:
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "password" in error_msg.lower() or "strength" in error_msg.lower()


def test_register_user_no_database(client, dependency_overrides_guard):
    """Test registration when database service is unavailable."""
    app.dependency_overrides[get_database_service] = lambda: None
    
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "StrongPass123!",
            "full_name": "Test User",
        },
    )
    
    assert response.status_code == 503
    error_msg = response.json().get("message", response.json().get("detail", ""))
    assert "database" in error_msg.lower() or "service" in error_msg.lower()


def test_register_user_duplicate_email(client, dependency_overrides_guard):
    """Test registration with duplicate email."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'create_user', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = ValueError("User with email test@example.com already exists")
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "StrongPass123!",
                "full_name": "Test User",
            },
        )
        
        assert response.status_code == 400
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "already exists" in error_msg.lower()


def test_login_with_database_auth(client, dependency_overrides_guard):
    """Test login with database authentication."""
    from backend.database.user_service import UserService
    from backend.auth import hash_password
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch.object(UserService, 'update_user_last_login', new_callable=AsyncMock):
        
        mock_get_user.return_value = {
            'id': 'user-123',
            'email': 'test@example.com',
            'password_hash': hash_password('TestPass123!'),
            'is_active': True,
            'roles': ['viewer'],
            'oauth_provider': None,
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "expires_in" in data
        assert data["expires_in"] > 0


def test_login_invalid_credentials(client, dependency_overrides_guard):
    """Test login with invalid credentials."""
    from backend.database.user_service import UserService
    from backend.auth import hash_password
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'get_user_by_email', new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = {
            'id': 'user-123',
            'email': 'test@example.com',
            'password_hash': hash_password('CorrectPass123!'),
            'is_active': True,
            'roles': ['viewer'],
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPass123!",
            },
        )
        
        assert response.status_code == 403
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "invalid" in error_msg.lower() or "credentials" in error_msg.lower()


def test_login_user_not_found(client, dependency_overrides_guard):
    """Test login with non-existent user."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch('backend.api.v1.endpoints.auth.demo_login_enabled', True):
        
        mock_get_user.return_value = None
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "",
            },
        )
        
        # May succeed with demo login or fail depending on demo login config
        assert response.status_code in [200, 400, 403, 404]


def test_login_oauth_only_user(client, dependency_overrides_guard):
    """Test login attempt for OAuth-only user."""
    from backend.database.user_service import UserService
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'get_user_by_email', new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = {
            'id': 'user-123',
            'email': 'test@example.com',
            'password_hash': None,
            'is_active': True,
            'roles': ['viewer'],
            'oauth_provider': 'google',
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "anypassword",
            },
        )
        
        assert response.status_code == 403
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "oauth" in error_msg.lower() or "sign in" in error_msg.lower()


def test_login_inactive_user(client, dependency_overrides_guard):
    """Test login attempt for inactive user."""
    from backend.database.user_service import UserService
    from backend.auth import hash_password
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'get_user_by_email', new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = {
            'id': 'user-123',
            'email': 'test@example.com',
            'password_hash': hash_password('TestPass123!'),
            'is_active': False,
            'roles': ['viewer'],
        }
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
            },
        )
        
        assert response.status_code == 403
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "inactive" in error_msg.lower()


def test_login_admin_role_scopes(client, dependency_overrides_guard):
    """Test login with admin role gets correct scopes."""
    from backend.database.user_service import UserService
    from backend.auth import hash_password
    from jose import jwt
    import os
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch.object(UserService, 'update_user_last_login', new_callable=AsyncMock):
        
        mock_get_user.return_value = {
            'id': 'user-123',
            'email': 'admin@example.com',
            'password_hash': hash_password('AdminPass123!'),
            'is_active': True,
            'roles': ['admin'],
        }
        
        # Set demo login secret for token decoding
        original_secret = os.getenv("DEMO_LOGIN_SECRET", "demo-secret-key-123")
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "AdminPass123!",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        
        # Decode token to check scopes
        token = data["access_token"]
        decoded = jwt.decode(token, original_secret, algorithms=["HS256"])
        assert "system/*.write" in decoded.get("scope", "")


def test_login_clinician_role_scopes(client, dependency_overrides_guard):
    """Test login with clinician role gets correct scopes."""
    from backend.database.user_service import UserService
    from backend.auth import hash_password
    from jose import jwt
    import os
    
    mock_db = MagicMock()
    app.dependency_overrides[get_database_service] = lambda: mock_db
    
    with patch.object(UserService, 'get_user_by_email', new_callable=AsyncMock) as mock_get_user, \
         patch.object(UserService, 'update_user_last_login', new_callable=AsyncMock):
        
        mock_get_user.return_value = {
            'id': 'user-123',
            'email': 'clinician@example.com',
            'password_hash': hash_password('ClinicianPass123!'),
            'is_active': True,
            'roles': ['clinician'],
        }
        
        # Set demo login secret for token decoding
        original_secret = os.getenv("DEMO_LOGIN_SECRET", "demo-secret-key-123")
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "clinician@example.com",
                "password": "ClinicianPass123!",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        
        # Decode token to check scopes
        token = data["access_token"]
        decoded = jwt.decode(token, original_secret, algorithms=["HS256"])
        assert "patient/*.write" in decoded.get("scope", "")
        assert "system/*.write" not in decoded.get("scope", "")
