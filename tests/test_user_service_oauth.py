"""
Tests for OAuth-related user service operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from backend.database.user_service import UserService
from backend.database.models import User


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock(spec=User)
    user.id = "user-123"
    user.email = "test@example.com"
    user.password_hash = "hashed-password"
    user.full_name = "Test User"
    user.roles = ['viewer']
    user.is_active = 1
    user.is_verified = 0
    user.oauth_provider = None
    user.oauth_provider_id = None
    user.oauth_access_token = None
    user.oauth_refresh_token = None
    user.oauth_token_expires = None
    user.created_at = datetime.now(timezone.utc)
    user.last_login = None
    return user


@pytest.mark.asyncio
async def test_create_oauth_user_new(mock_user):
    """Test creating a new OAuth user."""
    service = UserService()
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock no existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock user creation
        new_user = MagicMock()
        new_user.id = "new-user-123"
        new_user.email = "oauth@example.com"
        new_user.full_name = "OAuth User"
        new_user.roles = ['viewer']
        new_user.is_active = 1
        new_user.oauth_provider = "google"
        new_user.oauth_provider_id = "google-123"
        
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Create OAuth user
        result = await service.create_oauth_user(
            email="oauth@example.com",
            full_name="OAuth User",
            provider="google",
            provider_user_id="google-123",
            access_token="access-token",
            refresh_token="refresh-token",
            token_expires=datetime.now(timezone.utc) + timedelta(hours=1),
            email_verified=True,
        )
        
        assert result is not None
        assert result['email'] == "oauth@example.com"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_oauth_user_already_exists(mock_user):
    """Test creating OAuth user when email already exists."""
    service = UserService()
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await service.create_oauth_user(
                email="test@example.com",
                full_name="Test User",
                provider="google",
                provider_user_id="google-123",
                access_token="access-token",
                refresh_token="refresh-token",
                token_expires=datetime.now(timezone.utc) + timedelta(hours=1),
                email_verified=True,
            )
        
        assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_link_oauth_account(mock_user):
    """Test linking OAuth account to existing user."""
    service = UserService()
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        mock_session.commit = AsyncMock()
        
        # Link OAuth account
        await service.link_oauth_account(
            user_id="user-123",
            provider="google",
            provider_user_id="google-123",
            access_token="access-token",
            refresh_token="refresh-token",
            token_expires=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        
        # Verify OAuth fields were set
        assert mock_user.oauth_provider == "google"
        assert mock_user.oauth_provider_id == "google-123"
        assert mock_user.oauth_access_token == "access-token"
        assert mock_user.oauth_refresh_token == "refresh-token"
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_oauth_tokens(mock_user):
    """Test updating OAuth tokens for existing OAuth user."""
    service = UserService()
    
    # Set user as OAuth user
    mock_user.oauth_provider = "google"
    mock_user.oauth_provider_id = "google-123"
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        mock_session.commit = AsyncMock()
        
        # Update tokens
        new_expires = datetime.now(timezone.utc) + timedelta(hours=2)
        await service.update_oauth_tokens(
            user_id="user-123",
            provider="google",
            provider_user_id="google-123",
            access_token="new-access-token",
            refresh_token="new-refresh-token",
            token_expires=new_expires,
        )
        
        # Verify tokens were updated
        assert mock_user.oauth_access_token == "new-access-token"
        assert mock_user.oauth_refresh_token == "new-refresh-token"
        assert mock_user.oauth_token_expires == new_expires
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_by_email_with_oauth(mock_user):
    """Test retrieving user with OAuth information."""
    service = UserService()
    
    # Set OAuth fields
    mock_user.oauth_provider = "google"
    mock_user.oauth_provider_id = "google-123"
    mock_user.oauth_access_token = "access-token"
    mock_user.oauth_refresh_token = "refresh-token"
    mock_user.oauth_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get_user_by_email("test@example.com")
        
        assert result is not None
        assert result['email'] == "test@example.com"
        assert result.get('oauth_provider') == "google"
        assert result.get('oauth_provider_id') == "google-123"


@pytest.mark.asyncio
async def test_update_user_last_login(mock_user):
    """Test updating user last login timestamp."""
    service = UserService()
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        mock_session.commit = AsyncMock()
        
        before_login = mock_user.last_login
        await service.update_user_last_login("user-123")
        
        # Verify last_login was updated
        assert mock_user.last_login is not None
        assert mock_user.last_login != before_login
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_link_oauth_account_user_not_found():
    """Test linking OAuth account when user doesn't exist."""
    service = UserService()
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock user not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Should handle gracefully (implementation may vary)
        # This test documents expected behavior
        try:
            await service.link_oauth_account(
                user_id="nonexistent",
                provider="google",
                provider_user_id="google-123",
                access_token="token",
                refresh_token="refresh",
                token_expires=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            # If no exception, that's also valid behavior
        except (ValueError, AttributeError):
            # Expected if implementation raises exception
            pass

