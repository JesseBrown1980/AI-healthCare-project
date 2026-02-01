
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from backend.calendar.google_calendar import GoogleCalendarService
import httpx

# Custom mock for AsyncClient to handle context manager correctly
class MockAsyncClient:
    def __init__(self, *args, **kwargs):
        self.post = MagicMock()
        self.get = MagicMock()
        self.delete = MagicMock()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.fixture
def mock_calendar_service():
    service = GoogleCalendarService(
        client_id="test_client_id",
        client_secret="test_client_secret",
        refresh_token="test_refresh_token"
    )
    return service

@pytest.mark.asyncio
async def test_refresh_access_token(mock_calendar_service):
    """Test successful token refresh."""
    mock_client = MockAsyncClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "new_access_token"}
    
    # Setup the coroutine return value for post
    async def async_post(*args, **kwargs):
        return mock_response
    mock_client.post.side_effect = async_post

    with patch("httpx.AsyncClient", return_value=mock_client):
        token = await mock_calendar_service._refresh_access_token()
        
        assert token == "new_access_token"
        assert mock_calendar_service.access_token == "new_access_token"
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert kwargs['data']['grant_type'] == 'refresh_token'

@pytest.mark.asyncio
async def test_refresh_access_token_failure(mock_calendar_service):
    """Test token refresh failure handling."""
    mock_client = MockAsyncClient()
    mock_response = MagicMock()
    mock_response.status_code = 400
    
    def raise_error():
        raise httpx.HTTPStatusError("Error", request=None, response=mock_response)
    mock_response.raise_for_status.side_effect = raise_error
    
    async def async_post(*args, **kwargs):
        mock_response.raise_for_status()
        return mock_response
    mock_client.post.side_effect = async_post

    with patch("httpx.AsyncClient", return_value=mock_client):
        token = await mock_calendar_service._refresh_access_token()
        assert token is None

@pytest.mark.asyncio
async def test_list_events_pagination(mock_calendar_service):
    """Test listing events with pagination parameters."""
    mock_calendar_service.access_token = "valid_token"
    mock_client = MockAsyncClient()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {"id": "evt1", "summary": "Event 1"},
            {"id": "evt2", "summary": "Event 2"}
        ]
    }
    
    async def async_get(*args, **kwargs):
        return mock_response
    mock_client.get.side_effect = async_get

    with patch("httpx.AsyncClient", return_value=mock_client):
        time_min = datetime(2023, 1, 1, tzinfo=timezone.utc)
        events = await mock_calendar_service.list_events(
            time_min=time_min,
            max_results=50
        )
        
        assert len(events) == 2
        assert events[0]['id'] == "evt1"
        
        mock_client.get.assert_called_once()
        _, kwargs = mock_client.get.call_args
        assert kwargs['params']['timeMin'] == time_min.isoformat()
        assert kwargs['params']['maxResults'] == 50

@pytest.mark.asyncio
async def test_delete_event_success(mock_calendar_service):
    """Test successful event deletion."""
    mock_calendar_service.access_token = "valid_token"
    mock_client = MockAsyncClient()
    
    mock_response = MagicMock()
    mock_response.status_code = 204
    
    async def async_delete(*args, **kwargs):
        return mock_response
    mock_client.delete.side_effect = async_delete

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await mock_calendar_service.delete_event(event_id="evt1")
        
        assert result is True
        mock_client.delete.assert_called_once()
        args, _ = mock_client.delete.call_args
        assert "events/evt1" in args[0]

@pytest.mark.asyncio
async def test_delete_event_failure(mock_calendar_service):
    """Test event deletion failure."""
    mock_calendar_service.access_token = "valid_token"
    mock_client = MockAsyncClient()
    
    mock_response = MagicMock()
    mock_response.status_code = 404
    
    def raise_error():
        raise httpx.HTTPStatusError("Not Found", request=None, response=mock_response)
    mock_response.raise_for_status.side_effect = raise_error
    
    async def async_delete(*args, **kwargs):
        mock_response.raise_for_status()
        return mock_response
    mock_client.delete.side_effect = async_delete

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await mock_calendar_service.delete_event(event_id="non_existent")
        assert result is False

@pytest.mark.asyncio
async def test_create_event_with_reminders(mock_calendar_service):
    """Test creating an event with custom reminders."""
    mock_calendar_service.access_token = "valid_token"
    mock_client = MockAsyncClient()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "new_evt_123"}
    
    async def async_post(*args, **kwargs):
        return mock_response
    mock_client.post.side_effect = async_post

    with patch("httpx.AsyncClient", return_value=mock_client):
        reminders = {
            "useDefault": False,
            "overrides": [{"method": "email", "minutes": 60}]
        }
        
        result = await mock_calendar_service.create_event(
            summary="Checkup",
            reminders=reminders
        )
        
        assert result['id'] == "new_evt_123"
        _, kwargs = mock_client.post.call_args
        payload = kwargs['json']
        assert payload['reminders'] == reminders
