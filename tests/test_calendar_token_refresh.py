"""
Tests for calendar integration token refresh functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.calendar.google_calendar import GoogleCalendarService
from backend.calendar.microsoft_calendar import MicrosoftCalendarService


@pytest.mark.asyncio
async def test_google_calendar_token_refresh_success():
    """Test successful Google Calendar token refresh."""
    service = GoogleCalendarService(
        client_id="test-client-id",
        client_secret="test-secret",
        refresh_token="test-refresh-token",
    )
    
    mock_response = {
        "access_token": "new-access-token",
        "expires_in": 3600,
    }
    
    with patch('backend.calendar.google_calendar.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response_obj)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        new_token = await service._refresh_access_token()
        
        assert new_token == "new-access-token"
        assert service.access_token == "new-access-token"


@pytest.mark.asyncio
async def test_google_calendar_token_refresh_no_refresh_token():
    """Test Google Calendar token refresh when refresh token is missing."""
    service = GoogleCalendarService(
        client_id="test-client-id",
        client_secret="test-secret",
        refresh_token=None,
    )
    
    new_token = await service._refresh_access_token()
    
    assert new_token is None


@pytest.mark.asyncio
async def test_google_calendar_token_refresh_failure():
    """Test Google Calendar token refresh when API call fails."""
    service = GoogleCalendarService(
        client_id="test-client-id",
        client_secret="test-secret",
        refresh_token="test-refresh-token",
    )
    
    with patch('backend.calendar.google_calendar.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("API Error"))
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        new_token = await service._refresh_access_token()
        
        assert new_token is None


@pytest.mark.asyncio
async def test_google_calendar_auto_refresh_on_expired_token():
    """Test that Google Calendar automatically refreshes token when expired."""
    service = GoogleCalendarService(
        client_id="test-client-id",
        client_secret="test-secret",
        access_token=None,  # Expired/missing
        refresh_token="test-refresh-token",
    )
    
    mock_token_response = {
        "access_token": "refreshed-token",
        "expires_in": 3600,
    }
    
    with patch.object(service, '_refresh_access_token', new_callable=AsyncMock) as mock_refresh:
        mock_refresh.return_value = "refreshed-token"
        
        headers = await service._get_headers()
        
        assert headers["Authorization"] == "Bearer refreshed-token"
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_microsoft_calendar_token_refresh_success():
    """Test successful Microsoft Calendar token refresh."""
    service = MicrosoftCalendarService(
        client_id="test-client-id",
        client_secret="test-secret",
        refresh_token="test-refresh-token",
    )
    
    mock_response = {
        "access_token": "new-access-token",
        "expires_in": 3600,
    }
    
    with patch('backend.calendar.microsoft_calendar.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response_obj = MagicMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response_obj)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        new_token = await service._refresh_access_token()
        
        assert new_token == "new-access-token"
        assert service.access_token == "new-access-token"


@pytest.mark.asyncio
async def test_microsoft_calendar_token_refresh_no_refresh_token():
    """Test Microsoft Calendar token refresh when refresh token is missing."""
    service = MicrosoftCalendarService(
        client_id="test-client-id",
        client_secret="test-secret",
        refresh_token=None,
    )
    
    new_token = await service._refresh_access_token()
    
    assert new_token is None


@pytest.mark.asyncio
async def test_microsoft_calendar_token_refresh_failure():
    """Test Microsoft Calendar token refresh when API call fails."""
    service = MicrosoftCalendarService(
        client_id="test-client-id",
        client_secret="test-secret",
        refresh_token="test-refresh-token",
    )
    
    with patch('backend.calendar.microsoft_calendar.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("API Error"))
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        new_token = await service._refresh_access_token()
        
        assert new_token is None


@pytest.mark.asyncio
async def test_microsoft_calendar_auto_refresh_on_expired_token():
    """Test that Microsoft Calendar automatically refreshes token when expired."""
    service = MicrosoftCalendarService(
        client_id="test-client-id",
        client_secret="test-secret",
        access_token=None,  # Expired/missing
        refresh_token="test-refresh-token",
    )
    
    async def mock_refresh():
        service.access_token = "refreshed-token"
        return "refreshed-token"
    
    with patch.object(service, '_refresh_access_token', side_effect=mock_refresh):
        headers = await service._get_headers()
        
        # After refresh, access_token should be set and used in headers
        assert service.access_token == "refreshed-token"
        assert headers["Authorization"] == "Bearer refreshed-token"
