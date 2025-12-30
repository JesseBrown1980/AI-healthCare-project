"""
Tests for calendar integration (Google and Microsoft).
"""

import pytest
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

