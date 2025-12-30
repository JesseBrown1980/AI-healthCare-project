"""
Tests for OAuth authentication endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta, timezone

from backend.api.v1.endpoints.oauth import (
    oauth_authorize,
    oauth_callback,
    _generate_state,
    _store_state,
    _verify_state,
    _clear_state,
)
from backend.auth.oauth import GoogleOAuthProvider, AppleOAuthProvider
from backend.database.service import DatabaseService


@pytest.fixture
def mock_db_service():
    """Mock database service."""
    service = MagicMock(spec=DatabaseService)
    return service


@pytest.fixture
def mock_google_provider():
    """Mock Google OAuth provider."""
    provider = MagicMock(spec=GoogleOAuthProvider)
    provider.client_id = "test-google-client-id"
    provider.get_authorization_url = Mock(return_value="https://accounts.google.com/oauth?state=test")
    provider.exchange_code_for_tokens = AsyncMock(return_value={
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "expires_in": 3600,
    })
    provider.get_user_info = AsyncMock(return_value={
        "sub": "google-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "verified_email": True,
    })
    return provider


@pytest.fixture
def mock_apple_provider():
    """Mock Apple OAuth provider."""
    provider = MagicMock(spec=AppleOAuthProvider)
    provider.client_id = "test-apple-client-id"
    provider.get_authorization_url = Mock(return_value="https://appleid.apple.com/auth?state=test")
    provider.exchange_code_for_tokens = AsyncMock(return_value={
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "expires_in": 3600,
        "id_token": "test-id-token",
    })
    provider.get_user_info_from_id_token = AsyncMock(return_value={
        "sub": "apple-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "email_verified": True,
    })
    return provider


def test_generate_state():
    """Test state token generation."""
    state1 = _generate_state()
    state2 = _generate_state()
    
    assert state1 != state2
    assert len(state1) > 0
    assert len(state2) > 0


def test_store_and_verify_state():
    """Test state storage and verification."""
    state = _generate_state()
    _store_state(state, "google", "/dashboard")
    
    state_data = _verify_state(state)
    assert state_data is not None
    assert state_data["provider"] == "google"
    assert state_data["redirect_after"] == "/dashboard"
    assert "created_at" in state_data


def test_verify_state_expired():
    """Test that expired states are rejected."""
    state = _generate_state()
    _store_state(state, "google")
    
    # Manually expire the state
    from backend.api.v1.endpoints.oauth import _oauth_states
    _oauth_states[state]["created_at"] = datetime.now(timezone.utc) - timedelta(minutes=11)
    
    state_data = _verify_state(state)
    assert state_data is None


def test_clear_state():
    """Test state clearing."""
    state = _generate_state()
    _store_state(state, "google")
    
    assert _verify_state(state) is not None
    _clear_state(state)
    assert _verify_state(state) is None


@pytest.mark.asyncio
async def test_oauth_authorize_google(mock_db_service, mock_google_provider):
    """Test OAuth authorization for Google."""
    from backend.api.v1.endpoints.oauth import get_oauth_provider
    
    with patch('backend.api.v1.endpoints.oauth.get_oauth_provider', return_value=mock_google_provider):
        from fastapi import Request
        from fastapi.responses import RedirectResponse
        
        request = MagicMock(spec=Request)
        
        response = await oauth_authorize(
            provider="google",
            redirect_after="/dashboard",
            db_service=mock_db_service,
        )
        
        assert isinstance(response, RedirectResponse)
        assert "accounts.google.com" in response.headers["location"]


@pytest.mark.asyncio
async def test_oauth_authorize_invalid_provider(mock_db_service):
    """Test OAuth authorization with invalid provider."""
    with pytest.raises(HTTPException) as exc_info:
        await oauth_authorize(
            provider="invalid",
            redirect_after=None,
            db_service=mock_db_service,
        )
    
    assert exc_info.value.status_code == 400
    assert "Unsupported" in exc_info.value.detail


@pytest.mark.asyncio
async def test_oauth_authorize_no_database():
    """Test OAuth authorization without database service."""
    with pytest.raises(HTTPException) as exc_info:
        await oauth_authorize(
            provider="google",
            redirect_after=None,
            db_service=None,
        )
    
    assert exc_info.value.status_code == 503
    assert "database service" in exc_info.value.detail


@pytest.mark.asyncio
async def test_oauth_callback_google_success(mock_db_service, mock_google_provider):
    """Test successful OAuth callback for Google."""
    from backend.api.v1.endpoints.oauth import get_oauth_provider
    from backend.database.user_service import UserService
    
    # Setup state
    state = _generate_state()
    _store_state(state, "google", "/dashboard")
    
    # Mock user service
    mock_user_service = MagicMock(spec=UserService)
    mock_user_service.get_user_by_email = AsyncMock(return_value=None)  # New user
    mock_user_service.create_oauth_user = AsyncMock(return_value={
        "id": "user-123",
        "email": "test@example.com",
        "roles": ["viewer"],
    })
    mock_user_service.update_user_last_login = AsyncMock()
    
    with patch('backend.api.v1.endpoints.oauth.get_oauth_provider', return_value=mock_google_provider), \
         patch('backend.api.v1.endpoints.oauth.UserService', return_value=mock_user_service), \
         patch('backend.api.v1.endpoints.oauth._issue_demo_token') as mock_token, \
         patch.dict('os.environ', {'FRONTEND_URL': 'http://localhost:8501'}):
        
        mock_token.return_value = MagicMock(access_token="test-jwt-token")
        
        response = await oauth_callback(
            provider="google",
            code="test-auth-code",
            state=state,
            error=None,
            error_description=None,
            db_service=mock_db_service,
        )
        
        # Response should be a RedirectResponse
        assert hasattr(response, 'headers') or isinstance(response, RedirectResponse)
        assert "localhost:8501" in response.headers["location"]
        assert "token=" in response.headers["location"]


@pytest.mark.asyncio
async def test_oauth_callback_invalid_state(mock_db_service):
    """Test OAuth callback with invalid state."""
    with pytest.raises(HTTPException) as exc_info:
        await oauth_callback(
            provider="google",
            code="test-code",
            state="invalid-state",
            error=None,
            error_description=None,
            db_service=mock_db_service,
        )
    
    assert exc_info.value.status_code == 400
    assert "Invalid or expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_oauth_callback_provider_error(mock_db_service):
    """Test OAuth callback with provider error."""
    with pytest.raises(HTTPException) as exc_info:
        await oauth_callback(
            provider="google",
            code="test-code",
            state=_generate_state(),
            error="access_denied",
            error_description="User denied access",
            db_service=mock_db_service,
        )
    
    assert exc_info.value.status_code == 400
    assert "access_denied" in exc_info.value.detail or "denied" in exc_info.value.detail


@pytest.mark.asyncio
async def test_oauth_callback_missing_code(mock_db_service):
    """Test OAuth callback with missing authorization code."""
    state = _generate_state()
    _store_state(state, "google")
    
    with pytest.raises(HTTPException) as exc_info:
        await oauth_callback(
            provider="google",
            code="",
            state=state,
            error=None,
            error_description=None,
            db_service=mock_db_service,
        )
    
    assert exc_info.value.status_code == 400
    assert "required" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_oauth_callback_token_exchange_failure(mock_db_service, mock_google_provider):
    """Test OAuth callback when token exchange fails."""
    from backend.api.v1.endpoints.oauth import get_oauth_provider
    
    # Make token exchange fail
    mock_google_provider.exchange_code_for_tokens = AsyncMock(side_effect=Exception("Token exchange failed"))
    
    state = _generate_state()
    _store_state(state, "google")
    
    with patch('backend.api.v1.endpoints.oauth.get_oauth_provider', return_value=mock_google_provider):
        with pytest.raises(HTTPException) as exc_info:
            await oauth_callback(
                provider="google",
                code="test-code",
                state=state,
                error=None,
                error_description=None,
                db_service=mock_db_service,
            )
        
        assert exc_info.value.status_code == 400
        assert "exchange" in exc_info.value.detail.lower() or "failed" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_oauth_callback_missing_email(mock_db_service, mock_google_provider):
    """Test OAuth callback when provider doesn't return email."""
    from backend.api.v1.endpoints.oauth import get_oauth_provider
    
    # Make user info return no email
    mock_google_provider.get_user_info = AsyncMock(return_value={
        "sub": "user-123",
        "name": "Test User",
        # No email
    })
    
    state = _generate_state()
    _store_state(state, "google")
    
    with patch('backend.api.v1.endpoints.oauth.get_oauth_provider', return_value=mock_google_provider):
        with pytest.raises(HTTPException) as exc_info:
            await oauth_callback(
                provider="google",
                code="test-code",
                state=state,
                error=None,
                error_description=None,
                db_service=mock_db_service,
            )
        
        assert exc_info.value.status_code == 400
        assert "email" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_oauth_callback_existing_user_linking(mock_db_service, mock_google_provider):
    """Test OAuth callback for existing user linking OAuth account."""
    from backend.api.v1.endpoints.oauth import get_oauth_provider
    from backend.database.user_service import UserService
    
    state = _generate_state()
    _store_state(state, "google")
    
    # Mock existing user without OAuth
    mock_user_service = MagicMock(spec=UserService)
    mock_user_service.get_user_by_email = AsyncMock(return_value={
        "id": "user-123",
        "email": "test@example.com",
        "oauth_provider": None,  # No OAuth linked yet
    })
    mock_user_service.link_oauth_account = AsyncMock()
    mock_user_service.update_user_last_login = AsyncMock()
    
    with patch('backend.api.v1.endpoints.oauth.get_oauth_provider', return_value=mock_google_provider), \
         patch('backend.api.v1.endpoints.oauth.UserService', return_value=mock_user_service), \
         patch('backend.api.v1.endpoints.oauth._issue_demo_token') as mock_token, \
         patch.dict('os.environ', {'FRONTEND_URL': 'http://localhost:8501'}):
        
        mock_token.return_value = MagicMock(access_token="test-jwt-token")
        
        response = await oauth_callback(
            provider="google",
            code="test-code",
            state=state,
            error=None,
            error_description=None,
            db_service=mock_db_service,
        )
        
        # Verify OAuth account was linked
        mock_user_service.link_oauth_account.assert_called_once()
        # Response should be a RedirectResponse
        assert hasattr(response, 'headers') or isinstance(response, RedirectResponse)


@pytest.mark.asyncio
async def test_oauth_callback_provider_mismatch(mock_db_service):
    """Test OAuth callback with provider mismatch in state."""
    state = _generate_state()
    _store_state(state, "apple")  # State says apple
    
    with pytest.raises(HTTPException) as exc_info:
        await oauth_callback(
            provider="google",  # But callback is for google
            code="test-code",
            state=state,
            error=None,
            error_description=None,
            db_service=mock_db_service,
        )
    
    assert exc_info.value.status_code == 400
    assert "mismatch" in exc_info.value.detail.lower()

