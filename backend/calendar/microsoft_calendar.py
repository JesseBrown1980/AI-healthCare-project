"""
Microsoft Calendar/Outlook integration for appointment scheduling and reminders.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class MicrosoftCalendarService:
    """Service for Microsoft Calendar/Outlook integration."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("MICROSOFT_CALENDAR_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("MICROSOFT_CALENDAR_CLIENT_SECRET", "")
        self.access_token = access_token or os.getenv("MICROSOFT_CALENDAR_ACCESS_TOKEN", "")
        self.refresh_token = refresh_token or os.getenv("MICROSOFT_CALENDAR_REFRESH_TOKEN", "")
        self.tenant_id = tenant_id or os.getenv("MICROSOFT_TENANT_ID", "common")
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.graph_api_url = "https://graph.microsoft.com/v1.0"
    
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
                        "scope": "https://graph.microsoft.com/Calendars.ReadWrite",
                    }
                )
                response.raise_for_status()
                data = response.json()
                self.access_token = data.get("access_token")
                return self.access_token
        except Exception as e:
            logger.error(f"Failed to refresh Microsoft Calendar token: {e}")
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
        calendar_id: str = "calendar",
        subject: str = "",
        body: str = "",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: Optional[Dict[str, Any]] = None,
        attendees: Optional[List[Dict[str, Any]]] = None,
        reminder_minutes: int = 15,
    ) -> Optional[Dict[str, Any]]:
        """Create a calendar event."""
        if not start_time:
            start_time = datetime.now(timezone.utc)
        if not end_time:
            end_time = start_time + timedelta(hours=1)
        
        event = {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body,
            },
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC",
            },
            "isReminderOn": True,
            "reminderMinutesBeforeStart": reminder_minutes,
        }
        
        if location:
            event["location"] = location
        
        if attendees:
            event["attendees"] = attendees
        
        try:
            headers = await self._get_headers()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.graph_api_url}/me/calendars/{calendar_id}/events",
                    json=event,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to create Microsoft Calendar event: {e}")
            return None
    
    async def list_events(
        self,
        calendar_id: str = "calendar",
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        top: int = 10,
    ) -> List[Dict[str, Any]]:
        """List calendar events."""
        params = {
            "$top": top,
            "$orderby": "start/dateTime",
        }
        
        if start_datetime:
            params["$filter"] = f"start/dateTime ge '{start_datetime.isoformat()}'"
        if end_datetime:
            filter_clause = params.get("$filter", "")
            if filter_clause:
                params["$filter"] = f"{filter_clause} and end/dateTime le '{end_datetime.isoformat()}'"
            else:
                params["$filter"] = f"end/dateTime le '{end_datetime.isoformat()}'"
        
        try:
            headers = await self._get_headers()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.graph_api_url}/me/calendars/{calendar_id}/events",
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("value", [])
        except Exception as e:
            logger.error(f"Failed to list Microsoft Calendar events: {e}")
            return []
    
    async def delete_event(
        self,
        calendar_id: str = "calendar",
        event_id: str = "",
    ) -> bool:
        """Delete a calendar event."""
        try:
            headers = await self._get_headers()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(
                    f"{self.graph_api_url}/me/calendars/{calendar_id}/events/{event_id}",
                    headers=headers,
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to delete Microsoft Calendar event: {e}")
            return False

