"""
Calendar integration API endpoints for Google Calendar and Microsoft Calendar.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from backend.security import TokenContext, auth_dependency
from backend.calendar import GoogleCalendarService, MicrosoftCalendarService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/google/events")
async def create_google_calendar_event(
    event_data: Dict[str, Any] = Body(...),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.write"})
    ),
):
    """Create a Google Calendar event."""
    try:
        service = GoogleCalendarService()
        result = await service.create_event(
            calendar_id=event_data.get("calendar_id", "primary"),
            summary=event_data.get("summary", ""),
            description=event_data.get("description", ""),
            start_time=datetime.fromisoformat(event_data["start_time"]) if event_data.get("start_time") else None,
            end_time=datetime.fromisoformat(event_data["end_time"]) if event_data.get("end_time") else None,
            location=event_data.get("location"),
            attendees=event_data.get("attendees"),
            reminders=event_data.get("reminders"),
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create calendar event")
        
        return {"status": "success", "event": result}
    except Exception as e:
        logger.error(f"Failed to create Google Calendar event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/google/events")
async def list_google_calendar_events(
    calendar_id: str = Query("primary"),
    days_ahead: int = Query(30, ge=1, le=365),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read"})
    ),
):
    """List Google Calendar events."""
    try:
        service = GoogleCalendarService()
        time_min = datetime.now()
        time_max = datetime.now() + timedelta(days=days_ahead)
        
        events = await service.list_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
        )
        
        return {"status": "success", "events": events, "count": len(events)}
    except Exception as e:
        logger.error(f"Failed to list Google Calendar events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/microsoft/events")
async def create_microsoft_calendar_event(
    event_data: Dict[str, Any] = Body(...),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.write"})
    ),
):
    """Create a Microsoft Calendar event."""
    try:
        service = MicrosoftCalendarService()
        result = await service.create_event(
            calendar_id=event_data.get("calendar_id", "calendar"),
            subject=event_data.get("subject", ""),
            body=event_data.get("body", ""),
            start_time=datetime.fromisoformat(event_data["start_time"]) if event_data.get("start_time") else None,
            end_time=datetime.fromisoformat(event_data["end_time"]) if event_data.get("end_time") else None,
            location=event_data.get("location"),
            attendees=event_data.get("attendees"),
            reminder_minutes=event_data.get("reminder_minutes", 15),
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create calendar event")
        
        return {"status": "success", "event": result}
    except Exception as e:
        logger.error(f"Failed to create Microsoft Calendar event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/microsoft/events")
async def list_microsoft_calendar_events(
    calendar_id: str = Query("calendar"),
    days_ahead: int = Query(30, ge=1, le=365),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read"})
    ),
):
    """List Microsoft Calendar events."""
    try:
        service = MicrosoftCalendarService()
        start_datetime = datetime.now()
        end_datetime = datetime.now() + timedelta(days=days_ahead)
        
        events = await service.list_events(
            calendar_id=calendar_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
        
        return {"status": "success", "events": events, "count": len(events)}
    except Exception as e:
        logger.error(f"Failed to list Microsoft Calendar events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/google/events/{event_id}")
async def delete_google_calendar_event(
    event_id: str,
    calendar_id: str = Query("primary"),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.write"})
    ),
):
    """Delete a Google Calendar event."""
    try:
        service = GoogleCalendarService()
        success = await service.delete_event(
            calendar_id=calendar_id,
            event_id=event_id,
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete calendar event")
        
        return {"status": "success", "message": "Event deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete Google Calendar event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/microsoft/events/{event_id}")
async def delete_microsoft_calendar_event(
    event_id: str,
    calendar_id: str = Query("calendar"),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.write"})
    ),
):
    """Delete a Microsoft Calendar event."""
    try:
        service = MicrosoftCalendarService()
        success = await service.delete_event(
            calendar_id=calendar_id,
            event_id=event_id,
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete calendar event")
        
        return {"status": "success", "message": "Event deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete Microsoft Calendar event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
