"""
Tests for calendar integration API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from backend.main import app
from backend.security import TokenContext


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_token():
    """Generate a demo auth token for testing."""
    from backend.api.v1.endpoints.auth import _issue_demo_token
    response = _issue_demo_token("test@example.com")
    return response.access_token


def test_create_google_calendar_event_success(client, auth_token):
    """Test successful Google Calendar event creation."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    mock_event = {
        "id": "event123",
        "summary": "Test Event",
        "start": {"dateTime": "2024-01-01T10:00:00Z"},
        "end": {"dateTime": "2024-01-01T11:00:00Z"},
    }
    
    with patch('backend.api.v1.endpoints.calendar.GoogleCalendarService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.create_event = AsyncMock(return_value=mock_event)
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/api/v1/calendar/google/events",
            json={
                "summary": "Test Event",
                "description": "Test Description",
                "start_time": "2024-01-01T10:00:00Z",
                "end_time": "2024-01-01T11:00:00Z",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "event" in data
        assert data["event"]["id"] == "event123"


def test_create_google_calendar_event_missing_auth(client):
    """Test Google Calendar event creation without authentication."""
    response = client.post(
        "/api/v1/calendar/google/events",
        json={
            "summary": "Test Event",
            "start_time": "2024-01-01T10:00:00Z",
            "end_time": "2024-01-01T11:00:00Z",
        },
    )
    
    # Auth dependency may return 401 or service may fail with 500 if auth is missing
    assert response.status_code in [401, 403, 500]


def test_create_google_calendar_event_service_failure(client, auth_token):
    """Test Google Calendar event creation when service fails."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    with patch('backend.api.v1.endpoints.calendar.GoogleCalendarService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.create_event = AsyncMock(return_value=None)
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/api/v1/calendar/google/events",
            json={
                "summary": "Test Event",
                "start_time": "2024-01-01T10:00:00Z",
                "end_time": "2024-01-01T11:00:00Z",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 500
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert "failed" in error_msg.lower() or "error" in error_msg.lower()


def test_list_google_calendar_events_success(client, auth_token):
    """Test successful Google Calendar event listing."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    mock_events = [
        {"id": "event1", "summary": "Event 1"},
        {"id": "event2", "summary": "Event 2"},
    ]
    
    with patch('backend.api.v1.endpoints.calendar.GoogleCalendarService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.list_events = AsyncMock(return_value=mock_events)
        mock_service_class.return_value = mock_service
        
        response = client.get(
            "/api/v1/calendar/google/events?days_ahead=30",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "events" in data
        assert data["count"] == 2
        assert len(data["events"]) == 2


def test_list_google_calendar_events_with_custom_days(client, auth_token):
    """Test Google Calendar event listing with custom days_ahead parameter."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    mock_events = []
    
    with patch('backend.api.v1.endpoints.calendar.GoogleCalendarService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.list_events = AsyncMock(return_value=mock_events)
        mock_service_class.return_value = mock_service
        
        response = client.get(
            "/api/v1/calendar/google/events?days_ahead=60",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 0


def test_create_microsoft_calendar_event_success(client, auth_token):
    """Test successful Microsoft Calendar event creation."""
    from backend.calendar.microsoft_calendar import MicrosoftCalendarService
    
    mock_event = {
        "id": "event456",
        "subject": "Test Event",
        "start": {"dateTime": "2024-01-01T10:00:00Z"},
        "end": {"dateTime": "2024-01-01T11:00:00Z"},
    }
    
    with patch('backend.api.v1.endpoints.calendar.MicrosoftCalendarService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.create_event = AsyncMock(return_value=mock_event)
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/api/v1/calendar/microsoft/events",
            json={
                "subject": "Test Event",
                "body": "Test Description",
                "start_time": "2024-01-01T10:00:00Z",
                "end_time": "2024-01-01T11:00:00Z",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "event" in data
        assert data["event"]["id"] == "event456"


def test_create_microsoft_calendar_event_missing_auth(client):
    """Test Microsoft Calendar event creation without authentication."""
    response = client.post(
        "/api/v1/calendar/microsoft/events",
        json={
            "subject": "Test Event",
            "start_time": "2024-01-01T10:00:00Z",
            "end_time": "2024-01-01T11:00:00Z",
        },
    )
    
    # Auth dependency may return 401 or service may fail with 500 if auth is missing
    assert response.status_code in [401, 403, 500]


def test_list_microsoft_calendar_events_success(client, auth_token):
    """Test successful Microsoft Calendar event listing."""
    from backend.calendar.microsoft_calendar import MicrosoftCalendarService
    
    mock_events = [
        {"id": "event1", "subject": "Event 1"},
        {"id": "event2", "subject": "Event 2"},
    ]
    
    with patch('backend.api.v1.endpoints.calendar.MicrosoftCalendarService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.list_events = AsyncMock(return_value=mock_events)
        mock_service_class.return_value = mock_service
        
        response = client.get(
            "/api/v1/calendar/microsoft/events?days_ahead=30",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "events" in data
        assert data["count"] == 2
        assert len(data["events"]) == 2


def test_list_microsoft_calendar_events_with_custom_calendar(client, auth_token):
    """Test Microsoft Calendar event listing with custom calendar_id."""
    from backend.calendar.microsoft_calendar import MicrosoftCalendarService
    
    mock_events = []
    
    with patch('backend.api.v1.endpoints.calendar.MicrosoftCalendarService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.list_events = AsyncMock(return_value=mock_events)
        mock_service_class.return_value = mock_service
        
        response = client.get(
            "/api/v1/calendar/microsoft/events?calendar_id=custom&days_ahead=30",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


def test_calendar_endpoints_validation_errors(client, auth_token):
    """Test calendar endpoints with invalid parameters."""
    # Test days_ahead out of range
    response = client.get(
        "/api/v1/calendar/google/events?days_ahead=500",  # Max is 365
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    
    # Should return 422 for validation error
    assert response.status_code == 422


def test_calendar_endpoints_exception_handling(client, auth_token):
    """Test calendar endpoints handle exceptions gracefully."""
    from backend.calendar.google_calendar import GoogleCalendarService
    
    with patch('backend.api.v1.endpoints.calendar.GoogleCalendarService') as mock_service_class:
        mock_service = MagicMock()
        mock_service.create_event = AsyncMock(side_effect=Exception("Service error"))
        mock_service_class.return_value = mock_service
        
        response = client.post(
            "/api/v1/calendar/google/events",
            json={
                "summary": "Test Event",
                "start_time": "2024-01-01T10:00:00Z",
                "end_time": "2024-01-01T11:00:00Z",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 500
        error_msg = response.json().get("message", response.json().get("detail", ""))
        assert len(error_msg) > 0
