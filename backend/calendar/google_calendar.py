"""
Google Calendar integration for appointment scheduling and reminders.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Service for Google Calendar integration."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("GOOGLE_CALENDAR_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET", "")
        self.access_token = access_token or os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN", "")
        self.refresh_token = refresh_token or os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN", "")
        self.token_url = "https://oauth2.googleapis.com/token"
        self.calendar_api_url = "https://www.googleapis.com/calendar/v3"
    
    async def _refresh_access_token(self) -> Optional[str]:
        """Refresh the access token using refresh token."""
        if not self.refresh_token:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    }
                )
                response.raise_for_status()
                data = response.json()
                self.access_token = data.get("access_token")
                return self.access_token
        except Exception as e:
            logger.error(f"Failed to refresh Google Calendar token: {e}")
            return None
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers, refreshing token if needed."""
        if not self.access_token:
            await self._refresh_access_token()
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
    
    async def create_event(
        self,
        calendar_id: str = "primary",
        summary: str = "",
        description: str = "",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        reminders: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a calendar event."""
        if not start_time:
            start_time = datetime.now(timezone.utc)
        if not end_time:
            end_time = start_time + timedelta(hours=1)
        
        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC",
            },
        }
        
        if location:
            event["location"] = location
        
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]
        
        if reminders:
            event["reminders"] = reminders
        else:
            # Default reminders: 15 minutes and 1 day before
            event["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 15},
                    {"method": "popup", "minutes": 15},
                    {"method": "email", "minutes": 24 * 60},  # 1 day
                ],
            }
        
        try:
            headers = await self._get_headers()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.calendar_api_url}/calendars/{calendar_id}/events",
                    json=event,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to create Google Calendar event: {e}")
            return None
    
    async def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """List calendar events."""
        params = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        
        if time_min:
            params["timeMin"] = time_min.isoformat()
        if time_max:
            params["timeMax"] = time_max.isoformat()
        
        try:
            headers = await self._get_headers()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.calendar_api_url}/calendars/{calendar_id}/events",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("items", [])
        except Exception as e:
            logger.error(f"Failed to list Google Calendar events: {e}")
            return []
    
    async def delete_event(
        self,
        calendar_id: str = "primary",
        event_id: str = "",
    ) -> bool:
        """Delete a calendar event."""
        try:
            headers = await self._get_headers()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(
                    f"{self.calendar_api_url}/calendars/{calendar_id}/events/{event_id}",
                    headers=headers,
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to delete Google Calendar event: {e}")
            return False

