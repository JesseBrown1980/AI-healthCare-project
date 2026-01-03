"""
Tests for calendar integration (Google and Microsoft).
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_google_calendar_create_event():
    """Test Google Calendar event creation."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    service = GoogleCalendarService(
        client_id="test_client",
        client_secret="test_secret",
        access_token="test_token"
    )
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "event123", "summary": "Test Event"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await service.create_event(
            summary="Test Event",
            description="Test Description",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        assert result is not None
        assert result.get("id") == "event123"


@pytest.mark.asyncio
async def test_microsoft_calendar_create_event():
    """Test Microsoft Calendar event creation."""
    from backend.calendar.microsoft_calendar import MicrosoftCalendarService
    
    service = MicrosoftCalendarService(
        client_id="test_client",
        client_secret="test_secret",
        access_token="test_token"
    )
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "event456", "subject": "Test Event"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await service.create_event(
            subject="Test Event",
            body="Test Description",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        assert result is not None
        assert result.get("id") == "event456"


@pytest.mark.asyncio
async def test_calendar_list_events():
    """Test listing calendar events."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    service = GoogleCalendarService(access_token="test_token")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {"id": "event1", "summary": "Event 1"},
                {"id": "event2", "summary": "Event 2"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        events = await service.list_events()
        
        assert len(events) == 2
        assert events[0]["id"] == "event1"


@pytest.mark.asyncio
async def test_google_calendar_token_refresh():
    """Test Google Calendar token refresh logic."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    service = GoogleCalendarService(
        client_id="test_client",
        client_secret="test_secret",
        refresh_token="test_refresh_token"
    )
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "new_access_token"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        new_token = await service._refresh_access_token()
        
        assert new_token == "new_access_token"
        assert service.access_token == "new_access_token"


@pytest.mark.asyncio
async def test_microsoft_calendar_token_refresh():
    """Test Microsoft Calendar token refresh logic."""
    from backend.calendar.microsoft_calendar import MicrosoftCalendarService
    
    service = MicrosoftCalendarService(
        client_id="test_client",
        client_secret="test_secret",
        refresh_token="test_refresh_token"
    )
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "new_access_token"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        new_token = await service._refresh_access_token()
        
        assert new_token == "new_access_token"
        assert service.access_token == "new_access_token"


@pytest.mark.asyncio
async def test_google_calendar_token_refresh_no_refresh_token():
    """Test token refresh when no refresh token is available."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    service = GoogleCalendarService(
        client_id="test_client",
        client_secret="test_secret",
        refresh_token=None
    )
    
    new_token = await service._refresh_access_token()
    
    assert new_token is None


@pytest.mark.asyncio
async def test_google_calendar_delete_event():
    """Test Google Calendar event deletion."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    service = GoogleCalendarService(access_token="test_token")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 204  # No content for successful delete
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await service.delete_event(calendar_id="primary", event_id="event123")
        
        assert result is True


@pytest.mark.asyncio
async def test_microsoft_calendar_delete_event():
    """Test Microsoft Calendar event deletion."""
    from backend.calendar.microsoft_calendar import MicrosoftCalendarService
    
    service = MicrosoftCalendarService(access_token="test_token")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 204  # No content for successful delete
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await service.delete_event(calendar_id="calendar", event_id="event456")
        
        assert result is True


@pytest.mark.asyncio
async def test_microsoft_calendar_list_events():
    """Test listing Microsoft Calendar events."""
    from backend.calendar.microsoft_calendar import MicrosoftCalendarService
    
    service = MicrosoftCalendarService(access_token="test_token")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {"id": "event1", "subject": "Event 1"},
                {"id": "event2", "subject": "Event 2"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        events = await service.list_events()
        
        assert len(events) == 2
        assert events[0]["id"] == "event1"


@pytest.mark.asyncio
async def test_google_calendar_token_expiration_handling():
    """Test handling of expired tokens - verify _get_headers refreshes when no token."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    service = GoogleCalendarService(
        client_id="test_client",
        client_secret="test_secret",
        refresh_token="test_refresh_token"
    )
    # Set access_token to None to simulate expired token
    service.access_token = None
    
    with patch('httpx.AsyncClient') as mock_client_class:
        refresh_response = MagicMock()
        refresh_response.json.return_value = {"access_token": "new_token"}
        refresh_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=refresh_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test that _get_headers automatically refreshes when access_token is None
        headers = await service._get_headers()
        
        assert headers["Authorization"] == "Bearer new_token"
        assert service.access_token == "new_token"


@pytest.mark.asyncio
async def test_google_calendar_list_events_with_filters():
    """Test listing Google Calendar events with time filters."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    service = GoogleCalendarService(access_token="test_token")
    
    time_min = datetime.now(timezone.utc)
    time_max = datetime.now(timezone.utc) + timedelta(days=30)
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {"id": "event1", "summary": "Event 1"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        events = await service.list_events(
            calendar_id="primary",
            time_min=time_min,
            time_max=time_max,
            max_results=50
        )
        
        assert len(events) == 1
        assert events[0]["id"] == "event1"
        
        # Verify the GET was called with correct parameters
        call_args = mock_client.get.call_args
        assert "timeMin" in call_args.kwargs.get("params", {})
        assert "timeMax" in call_args.kwargs.get("params", {})


@pytest.mark.asyncio
async def test_microsoft_calendar_list_events_with_filters():
    """Test listing Microsoft Calendar events with time filters."""
    from backend.calendar.microsoft_calendar import MicrosoftCalendarService
    
    service = MicrosoftCalendarService(access_token="test_token")
    
    start_datetime = datetime.now(timezone.utc)
    end_datetime = datetime.now(timezone.utc) + timedelta(days=30)
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {"id": "event1", "subject": "Event 1"}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=mock_client)
        
        events = await service.list_events(
            calendar_id="calendar",
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            top=50
        )
        
        assert len(events) == 1
        assert events[0]["id"] == "event1"


@pytest.mark.asyncio
async def test_google_calendar_delete_event_failure():
    """Test Google Calendar event deletion failure handling."""
    from backend.calendar.google_calendar import GoogleCalendarService
    import httpx
    
    service = GoogleCalendarService(access_token="test_token")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await service.delete_event(calendar_id="primary", event_id="nonexistent")
        
        assert result is False


@pytest.mark.asyncio
async def test_microsoft_calendar_delete_event_failure():
    """Test Microsoft Calendar event deletion failure handling."""
    from backend.calendar.microsoft_calendar import MicrosoftCalendarService
    import httpx
    
    service = MicrosoftCalendarService(access_token="test_token")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await service.delete_event(calendar_id="calendar", event_id="nonexistent")
        
        assert result is False

