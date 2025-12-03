"""
Calendar integration API endpoints for Google Calendar and Microsoft Calendar.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from backend.security import TokenContext, auth_dependency
from backend.calendar import GoogleCalendarService, MicrosoftCalendarService
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured, log_service_error
from backend.utils.service_error_handler import ServiceErrorHandler
from backend.utils.validation import validate_query_string

router = APIRouter()


@router.post("/google/events")
async def create_google_calendar_event(
    request: Request,
    event_data: Dict[str, Any] = Body(...),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.write"})
    ),
):
    """Create a Google Calendar event."""
    correlation_id = get_correlation_id(request)
    
    try:
        # Validate input
        summary = event_data.get("summary", "").strip()
        if not summary:
            raise create_http_exception(
                message="Event summary is required",
                status_code=400,
                error_type="ValidationError"
            )
        
        # Validate description if provided
        description = event_data.get("description", "")
        if description:
            description = validate_query_string(description, max_length=5000)
        
        log_structured(
            level="info",
            message="Creating Google Calendar event",
            correlation_id=correlation_id,
            request=request,
            summary=summary[:50]  # Log first 50 chars
        )
        
        service = GoogleCalendarService()
        result = await service.create_event(
            calendar_id=event_data.get("calendar_id", "primary"),
            summary=summary,
            description=description,
            start_time=datetime.fromisoformat(event_data["start_time"]) if event_data.get("start_time") else None,
            end_time=datetime.fromisoformat(event_data["end_time"]) if event_data.get("end_time") else None,
            location=event_data.get("location"),
            attendees=event_data.get("attendees"),
            reminders=event_data.get("reminders"),
        )
        
        if not result:
            raise create_http_exception(
                message="Failed to create calendar event",
                status_code=500,
                error_type="ServiceError"
            )
        
        log_structured(
            level="info",
            message="Google Calendar event created successfully",
            correlation_id=correlation_id,
            request=request,
            event_id=result.get("id")
        )
        
        return {"status": "success", "event": result}
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "create_google_calendar_event", "provider": "google"},
            correlation_id,
            request
        )


@router.get("/google/events")
async def list_google_calendar_events(
    request: Request,
    calendar_id: str = Query("primary"),
    days_ahead: int = Query(30, ge=1, le=365),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read"})
    ),
):
    """List Google Calendar events."""
    correlation_id = get_correlation_id(request)
    
    try:
        log_structured(
            level="info",
            message="Listing Google Calendar events",
            correlation_id=correlation_id,
            request=request,
            calendar_id=calendar_id,
            days_ahead=days_ahead
        )
        
        service = GoogleCalendarService()
        time_min = datetime.now()
        time_max = datetime.now() + timedelta(days=days_ahead)
        
        events = await service.list_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
        )
        
        log_structured(
            level="info",
            message="Google Calendar events listed successfully",
            correlation_id=correlation_id,
            request=request,
            event_count=len(events)
        )
        
        return {"status": "success", "events": events, "count": len(events)}
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "list_google_calendar_events", "provider": "google"},
            correlation_id,
            request
        )


@router.post("/microsoft/events")
async def create_microsoft_calendar_event(
    request: Request,
    event_data: Dict[str, Any] = Body(...),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.write"})
    ),
):
    """Create a Microsoft Calendar event."""
    correlation_id = get_correlation_id(request)
    
    try:
        # Validate input
        subject = event_data.get("subject", "").strip()
        if not subject:
            raise create_http_exception(
                message="Event subject is required",
                status_code=400,
                error_type="ValidationError"
            )
        
        # Validate body if provided
        body = event_data.get("body", "")
        if body:
            body = validate_query_string(body, max_length=5000)
        
        log_structured(
            level="info",
            message="Creating Microsoft Calendar event",
            correlation_id=correlation_id,
            request=request,
            subject=subject[:50]  # Log first 50 chars
        )
        
        service = MicrosoftCalendarService()
        result = await service.create_event(
            calendar_id=event_data.get("calendar_id", "calendar"),
            subject=subject,
            body=body,
            start_time=datetime.fromisoformat(event_data["start_time"]) if event_data.get("start_time") else None,
            end_time=datetime.fromisoformat(event_data["end_time"]) if event_data.get("end_time") else None,
            location=event_data.get("location"),
            attendees=event_data.get("attendees"),
            reminder_minutes=event_data.get("reminder_minutes", 15),
        )
        
        if not result:
            raise create_http_exception(
                message="Failed to create calendar event",
                status_code=500,
                error_type="ServiceError"
            )
        
        log_structured(
            level="info",
            message="Microsoft Calendar event created successfully",
            correlation_id=correlation_id,
            request=request,
            event_id=result.get("id")
        )
        
        return {"status": "success", "event": result}
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "create_microsoft_calendar_event", "provider": "microsoft"},
            correlation_id,
            request
        )


@router.get("/microsoft/events")
async def list_microsoft_calendar_events(
    request: Request,
    calendar_id: str = Query("calendar"),
    days_ahead: int = Query(30, ge=1, le=365),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.read"})
    ),
):
    """List Microsoft Calendar events."""
    correlation_id = get_correlation_id(request)
    
    try:
        log_structured(
            level="info",
            message="Listing Microsoft Calendar events",
            correlation_id=correlation_id,
            request=request,
            calendar_id=calendar_id,
            days_ahead=days_ahead
        )
        
        service = MicrosoftCalendarService()
        start_datetime = datetime.now()
        end_datetime = datetime.now() + timedelta(days=days_ahead)
        
        events = await service.list_events(
            calendar_id=calendar_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
        
        log_structured(
            level="info",
            message="Microsoft Calendar events listed successfully",
            correlation_id=correlation_id,
            request=request,
            event_count=len(events)
        )
        
        return {"status": "success", "events": events, "count": len(events)}
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "list_microsoft_calendar_events", "provider": "microsoft"},
            correlation_id,
            request
        )


@router.delete("/google/events/{event_id}")
async def delete_google_calendar_event(
    request: Request,
    event_id: str,
    calendar_id: str = Query("primary"),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.write"})
    ),
):
    """Delete a Google Calendar event."""
    correlation_id = get_correlation_id(request)
    
    try:
        # Validate event_id (basic validation)
        if not event_id or len(event_id) > 255:
            raise create_http_exception(
                message="Invalid event ID",
                status_code=400,
                error_type="ValidationError"
            )
        
        log_structured(
            level="info",
            message="Deleting Google Calendar event",
            correlation_id=correlation_id,
            request=request,
            event_id=event_id,
            calendar_id=calendar_id
        )
        
        service = GoogleCalendarService()
        success = await service.delete_event(
            calendar_id=calendar_id,
            event_id=event_id,
        )
        
        if not success:
            raise create_http_exception(
                message="Failed to delete calendar event",
                status_code=500,
                error_type="ServiceError"
            )
        
        log_structured(
            level="info",
            message="Google Calendar event deleted successfully",
            correlation_id=correlation_id,
            request=request,
            event_id=event_id
        )
        
        return {"status": "success", "message": "Event deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "delete_google_calendar_event", "provider": "google", "event_id": event_id},
            correlation_id,
            request
        )


@router.delete("/microsoft/events/{event_id}")
async def delete_microsoft_calendar_event(
    request: Request,
    event_id: str,
    calendar_id: str = Query("calendar"),
    auth: TokenContext = Depends(
        auth_dependency({"patient/*.read", "user/*.write"})
    ),
):
    """Delete a Microsoft Calendar event."""
    correlation_id = get_correlation_id(request)
    
    try:
        # Validate event_id (basic validation)
        if not event_id or len(event_id) > 255:
            raise create_http_exception(
                message="Invalid event ID",
                status_code=400,
                error_type="ValidationError"
            )
        
        log_structured(
            level="info",
            message="Deleting Microsoft Calendar event",
            correlation_id=correlation_id,
            request=request,
            event_id=event_id,
            calendar_id=calendar_id
        )
        
        service = MicrosoftCalendarService()
        success = await service.delete_event(
            calendar_id=calendar_id,
            event_id=event_id,
        )
        
        if not success:
            raise create_http_exception(
                message="Failed to delete calendar event",
                status_code=500,
                error_type="ServiceError"
            )
        
        log_structured(
            level="info",
            message="Microsoft Calendar event deleted successfully",
            correlation_id=correlation_id,
            request=request,
            event_id=event_id
        )
        
        return {"status": "success", "message": "Event deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "delete_microsoft_calendar_event", "provider": "microsoft", "event_id": event_id},
            correlation_id,
            request
        )
