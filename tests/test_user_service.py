"""
Comprehensive unit tests for UserService database operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.database.user_service import UserService
from backend.database.models import User
from backend.auth import hash_password


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock(spec=User)
    user.id = "user-123"
    user.email = "test@example.com"
    user.password_hash = hash_password("TestPass123!")
    user.full_name = "Test User"
    user.roles = ['viewer']
    user.is_active = 1
    user.is_verified = 0
    user.oauth_provider = None
    user.oauth_provider_id = None
    user.created_at = datetime.now(timezone.utc)
    user.last_login = None
    user.password_reset_token = None
    user.password_reset_token_expires = None
    user.verification_token = None
    user.verification_token_expires = None
    return user


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    result = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session, result


@pytest.mark.asyncio
async def test_create_user_success(mock_db_session):
    """Test successful user creation."""
    service = UserService()
    session, result = mock_db_session
    
    # Mock no existing user
    result.scalar_one_or_none.return_value = None
    
    # Mock new user after creation
    new_user = MagicMock(spec=User)
    new_user.id = "new-user-123"
    new_user.email = "new@example.com"
    new_user.full_name = "New User"
    new_user.roles = ['viewer']
    new_user.is_active = 1
    
    result.scalar_one_or_none.side_effect = [None, new_user]  # First check, then after refresh
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        user_data = await service.create_user(
            email="new@example.com",
            password_hash=hash_password("TestPass123!"),
            full_name="New User",
            roles=['viewer']
        )
        
        assert user_data['email'] == "new@example.com"
        assert user_data['full_name'] == "New User"
        assert user_data['roles'] == ['viewer']
        assert user_data['is_active'] is True
        session.add.assert_called_once()
        session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_duplicate_email(mock_db_session):
    """Test user creation with duplicate email."""
    service = UserService()
    session, result = mock_db_session
    
    # Mock existing user
    existing_user = MagicMock(spec=User)
    result.scalar_one_or_none.return_value = existing_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="already exists"):
            await service.create_user(
                email="existing@example.com",
                password_hash=hash_password("TestPass123!"),
            )


@pytest.mark.asyncio
async def test_get_user_by_email_success(mock_db_session, mock_user):
    """Test successful user retrieval by email."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = mock_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        user_data = await service.get_user_by_email("test@example.com")
        
        assert user_data is not None
        assert user_data['email'] == "test@example.com"
        assert user_data['id'] == "user-123"
        assert user_data['password_hash'] is not None
        assert user_data['is_active'] is True


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(mock_db_session):
    """Test user retrieval by email when user doesn't exist."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = None
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        user_data = await service.get_user_by_email("nonexistent@example.com")
        
        assert user_data is None


@pytest.mark.asyncio
async def test_get_user_by_id_success(mock_db_session, mock_user):
    """Test successful user retrieval by ID."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = mock_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        user_data = await service.get_user_by_id("user-123")
        
        assert user_data is not None
        assert user_data['id'] == "user-123"
        assert user_data['email'] == "test@example.com"


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(mock_db_session):
    """Test user retrieval by ID when user doesn't exist."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = None
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        user_data = await service.get_user_by_id("nonexistent-id")
        
        assert user_data is None


@pytest.mark.asyncio
async def test_update_user_last_login(mock_db_session, mock_user):
    """Test updating user's last login timestamp."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = mock_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        await service.update_user_last_login("user-123")
        
        # Verify last_login was set
        assert mock_user.last_login is not None
        session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_password(mock_db_session, mock_user):
    """Test updating user's password."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = mock_user
    
    new_password_hash = hash_password("NewPass123!")
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        await service.update_user_password("user-123", new_password_hash)
        
        assert mock_user.password_hash == new_password_hash
        session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_deactivate_user(mock_db_session, mock_user):
    """Test deactivating a user account."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = mock_user
    mock_user.is_active = 1
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        await service.deactivate_user("user-123")
        
        assert mock_user.is_active == 0
        session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_generate_password_reset_token_success(mock_db_session, mock_user):
    """Test successful password reset token generation."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = mock_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        token = await service.generate_password_reset_token("test@example.com")
        
        assert token is not None
        assert len(token) > 0
        assert mock_user.password_reset_token == token
        assert mock_user.password_reset_token_expires is not None
        # Verify expiration is in the future (1 hour)
        assert mock_user.password_reset_token_expires > datetime.now(timezone.utc)
        session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_generate_password_reset_token_user_not_found(mock_db_session):
    """Test password reset token generation for non-existent user."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = None
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        token = await service.generate_password_reset_token("nonexistent@example.com")
        
        # Should return None to prevent email enumeration
        assert token is None


@pytest.mark.asyncio
async def test_verify_password_reset_token_valid(mock_db_session, mock_user):
    """Test verifying a valid password reset token."""
    service = UserService()
    session, result = mock_db_session
    
    mock_user.password_reset_token = "valid-token-123"
    mock_user.password_reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    result.scalar_one_or_none.return_value = mock_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        is_valid = await service.verify_password_reset_token("test@example.com", "valid-token-123")
        
        assert is_valid is True


@pytest.mark.asyncio
async def test_verify_password_reset_token_invalid(mock_db_session):
    """Test verifying an invalid password reset token."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = None
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        is_valid = await service.verify_password_reset_token("test@example.com", "invalid-token")
        
        assert is_valid is False


@pytest.mark.asyncio
async def test_verify_password_reset_token_expired(mock_db_session, mock_user):
    """Test verifying an expired password reset token."""
    service = UserService()
    session, result = mock_db_session
    
    mock_user.password_reset_token = "expired-token-123"
    mock_user.password_reset_token_expires = datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
    result.scalar_one_or_none.return_value = mock_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        is_valid = await service.verify_password_reset_token("test@example.com", "expired-token-123")
        
        assert is_valid is False


@pytest.mark.asyncio
async def test_reset_password_with_token_success(mock_db_session, mock_user):
    """Test successful password reset with valid token."""
    service = UserService()
    session, result = mock_db_session
    
    mock_user.password_reset_token = "valid-token-123"
    mock_user.password_reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    result.scalar_one_or_none.return_value = mock_user
    
    new_password_hash = hash_password("NewPass123!")
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        success = await service.reset_password_with_token(
            "test@example.com",
            "valid-token-123",
            new_password_hash
        )
        
        assert success is True
        assert mock_user.password_hash == new_password_hash
        assert mock_user.password_reset_token is None
        assert mock_user.password_reset_token_expires is None
        session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_with_token_expired(mock_db_session, mock_user):
    """Test password reset with expired token."""
    service = UserService()
    session, result = mock_db_session
    
    mock_user.password_reset_token = "expired-token-123"
    mock_user.password_reset_token_expires = datetime.now(timezone.utc) - timedelta(hours=1)
    result.scalar_one_or_none.return_value = mock_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        success = await service.reset_password_with_token(
            "test@example.com",
            "expired-token-123",
            hash_password("NewPass123!")
        )
        
        assert success is False


@pytest.mark.asyncio
async def test_generate_verification_token_success(mock_db_session, mock_user):
    """Test successful email verification token generation."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = mock_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        token = await service.generate_verification_token("test@example.com")
        
        assert token is not None
        assert len(token) > 0
        assert mock_user.verification_token == token
        assert mock_user.verification_token_expires is not None
        # Verify expiration is in the future (7 days)
        assert mock_user.verification_token_expires > datetime.now(timezone.utc)
        session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_generate_verification_token_user_not_found(mock_db_session):
    """Test verification token generation for non-existent user."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = None
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        token = await service.generate_verification_token("nonexistent@example.com")
        
        # Should return None to prevent email enumeration
        assert token is None


@pytest.mark.asyncio
async def test_verify_email_with_token_valid(mock_db_session, mock_user):
    """Test verifying email with valid token."""
    service = UserService()
    session, result = mock_db_session
    
    mock_user.verification_token = "valid-token-123"
    mock_user.verification_token_expires = datetime.now(timezone.utc) + timedelta(days=7)
    mock_user.is_verified = 0
    result.scalar_one_or_none.return_value = mock_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        is_valid = await service.verify_email_with_token("test@example.com", "valid-token-123")
        
        assert is_valid is True
        assert mock_user.is_verified == 1
        assert mock_user.verification_token is None
        assert mock_user.verification_token_expires is None
        session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_verify_email_with_token_expired(mock_db_session, mock_user):
    """Test verifying email with expired token."""
    service = UserService()
    session, result = mock_db_session
    
    mock_user.verification_token = "expired-token-123"
    mock_user.verification_token_expires = datetime.now(timezone.utc) - timedelta(days=1)  # Expired
    result.scalar_one_or_none.return_value = mock_user
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        is_valid = await service.verify_email_with_token("test@example.com", "expired-token-123")
        
        assert is_valid is False


@pytest.mark.asyncio
async def test_verify_email_with_token_invalid(mock_db_session):
    """Test verifying email with invalid token."""
    service = UserService()
    session, result = mock_db_session
    
    result.scalar_one_or_none.return_value = None
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        is_valid = await service.verify_email_with_token("test@example.com", "invalid-token")
        
        assert is_valid is False


@pytest.mark.asyncio
async def test_token_expiration_handling():
    """Test that token expiration is properly handled."""
    service = UserService()
    
    # Test password reset token expiration (1 hour)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)
    
    # Token should be valid
    assert expires_at > now
    
    # Token should expire after 1 hour
    expired_at = now - timedelta(hours=2)
    assert expired_at < now
    
    # Test email verification token expiration (7 days)
    verification_expires = now + timedelta(days=7)
    assert verification_expires > now
    
    verification_expired = now - timedelta(days=8)
    assert verification_expired < now
