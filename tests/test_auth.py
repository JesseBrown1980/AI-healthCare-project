"""
Tests for user authentication and registration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.auth import hash_password, verify_password, is_password_strong
from backend.database.user_service import UserService


@pytest.mark.asyncio
async def test_password_hashing():
    """Test password hashing and verification."""
    password = "TestPassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert len(hashed) > 0
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_password_strength_validation():
    """Test password strength requirements."""
    # Weak passwords
    assert is_password_strong("short")[0] is False
    assert is_password_strong("nouppercase123!")[0] is False
    assert is_password_strong("NOLOWERCASE123!")[0] is False
    assert is_password_strong("NoDigits!")[0] is False
    assert is_password_strong("NoSpecial123")[0] is False
    
    # Strong password
    is_strong, _ = is_password_strong("StrongPass123!")
    assert is_strong is True


@pytest.mark.asyncio
async def test_user_service_create_user():
    """Test user creation."""
    service = UserService()
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        # Setup async context manager
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock execute result - no existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Mock user object that will be created
        mock_user = MagicMock()
        mock_user.id = "test-id-123"
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"
        mock_user.roles = ['viewer']
        mock_user.is_active = 1
        
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Create user
        result = await service.create_user(
            email="test@example.com",
            password_hash=hash_password("TestPass123!"),
            full_name="Test User",
            roles=['viewer']
        )
        
        assert result is not None
        assert 'email' in result
        assert result['email'] == "test@example.com"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_user_service_get_user_by_email():
    """Test retrieving user by email."""
    service = UserService()
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Mock existing user
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.email = "test@example.com"
        mock_user.password_hash = hash_password("TestPass123!")
        mock_user.full_name = "Test User"
        mock_user.roles = ['viewer']
        mock_user.is_active = 1
        mock_user.is_verified = 0
        mock_user.created_at = None
        mock_user.last_login = None
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get_user_by_email("test@example.com")
        
        assert result is not None
        assert result['email'] == "test@example.com"
        assert result['id'] == "user-123"
        assert 'password_hash' in result


@pytest.mark.asyncio
async def test_user_service_get_user_by_email_not_found():
    """Test retrieving non-existent user."""
    service = UserService()
    
    with patch('backend.database.user_service.get_db_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await service.get_user_by_email("nonexistent@example.com")
        
        assert result is None


def test_password_reset_token_generation():
    """Test password reset token generation."""
    import secrets
    from datetime import datetime, timedelta, timezone
    
    # Generate a secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    assert len(token) > 0
    assert expires_at > datetime.now(timezone.utc)
    assert isinstance(token, str)

