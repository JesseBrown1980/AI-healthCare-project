"""
Audit Middleware
FastAPI middleware for automatic request/response audit logging.
"""

import time
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid

from .audit_logger import get_audit_logger
from .audit_events import (
    AuditEvent,
    AuditEventType,
    AuditEventCategory,
    AuditSeverity,
)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log API requests for audit purposes.
    
    Logs:
    - All requests with response status
    - Authentication attempts
    - Access denied responses
    - PHI access (when patient_id in path/query)
    """
    
    # Endpoints that should not be logged (health checks, metrics, etc.)
    EXCLUDED_PATHS = {
        "/health",
        "/metrics",
        "/favicon.ico",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    # Sensitive paths that require audit logging
    SENSITIVE_PATHS = {
        "/api/v1/patient",
        "/api/v1/analyze",
        "/api/v1/fhir",
    }
    
    def __init__(self, app, enabled: bool = True, log_all_requests: bool = False):
        super().__init__(app)
        self.enabled = enabled
        self.log_all_requests = log_all_requests
        self.audit = get_audit_logger()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)
        
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract actor from token (if available)
        actor = self._extract_actor(request)
        
        # Extract client info
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Check if this is a sensitive path
        is_sensitive = any(request.url.path.startswith(p) for p in self.SENSITIVE_PATHS)
        
        # Track timing
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            self._log_error(request, actor, str(e), request_id, ip_address)
            raise
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Determine if we should log this request
        should_log = (
            self.log_all_requests or
            is_sensitive or
            response.status_code >= 400 or
            request.method in ("POST", "PUT", "DELETE", "PATCH")
        )
        
        if should_log:
            self._log_request(
                request=request,
                response=response,
                actor=actor,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                duration_ms=duration_ms,
                is_sensitive=is_sensitive,
            )
        
        return response
    
    def _extract_actor(self, request: Request) -> str:
        """Extract actor (user ID) from request token."""
        # Try to get from already-validated token context
        if hasattr(request.state, "token_context"):
            return request.state.token_context.subject or "unknown"
        
        # Try to get from authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Return truncated token as identifier
            token = auth_header[7:]
            return f"token:{token[:8]}..."
        
        return "anonymous"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        # Check for forwarded headers (behind proxy)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _log_request(
        self,
        request: Request,
        response: Response,
        actor: str,
        request_id: str,
        ip_address: str,
        user_agent: str,
        duration_ms: float,
        is_sensitive: bool,
    ) -> None:
        """Log an API request."""
        # Determine event type based on response status
        if response.status_code == 401:
            event_type = AuditEventType.LOGIN_FAILURE
            category = AuditEventCategory.AUTHENTICATION
            severity = AuditSeverity.WARNING
        elif response.status_code == 403:
            event_type = AuditEventType.ACCESS_DENIED
            category = AuditEventCategory.AUTHORIZATION
            severity = AuditSeverity.WARNING
        elif response.status_code >= 500:
            event_type = AuditEventType.ERROR
            category = AuditEventCategory.SYSTEM
            severity = AuditSeverity.ERROR
        elif is_sensitive:
            event_type = AuditEventType.PHI_ACCESS
            category = AuditEventCategory.DATA_ACCESS
            severity = AuditSeverity.INFO
        else:
            event_type = AuditEventType.PATIENT_READ
            category = AuditEventCategory.DATA_ACCESS
            severity = AuditSeverity.INFO
        
        # Extract patient ID if present
        patient_id = self._extract_patient_id(request)
        
        event = AuditEvent(
            event_type=event_type,
            category=category,
            severity=severity,
            actor=actor,
            action=f"{request.method} {request.url.path}",
            outcome="success" if response.status_code < 400 else "failure",
            resource=request.url.path,
            patient_id=patient_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "query_params": dict(request.query_params),
            }
        )
        
        self.audit.log(event)
    
    def _log_error(
        self,
        request: Request,
        actor: str,
        error: str,
        request_id: str,
        ip_address: str,
    ) -> None:
        """Log an error event."""
        event = AuditEvent(
            event_type=AuditEventType.ERROR,
            category=AuditEventCategory.SYSTEM,
            severity=AuditSeverity.ERROR,
            actor=actor,
            action=f"Error processing {request.method} {request.url.path}",
            outcome="error",
            resource=request.url.path,
            request_id=request_id,
            ip_address=ip_address,
            details={"error": error}
        )
        
        self.audit.log(event)
    
    def _extract_patient_id(self, request: Request) -> Optional[str]:
        """Extract patient ID from request path or query params."""
        # Check path parameters
        path_parts = request.url.path.split("/")
        for i, part in enumerate(path_parts):
            if part in ("patient", "patients") and i + 1 < len(path_parts):
                return path_parts[i + 1]
        
        # Check query parameters
        patient_id = request.query_params.get("patient_id")
        if patient_id:
            return patient_id
        
        return None
