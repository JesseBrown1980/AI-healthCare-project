"""
Audit Logger
Centralized audit logging for SOC 2 compliance.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from .audit_events import (
    AuditEvent,
    AuditEventType,
    AuditEventCategory,
    AuditSeverity,
)


class AuditLogger:
    """
    Centralized audit logger for security and compliance events.
    
    Supports multiple outputs:
    - File (JSON lines format)
    - Console (structured logging)
    - Future: External SIEM integration
    
    Usage:
        audit = AuditLogger()
        audit.log(login_success(actor="user123"))
    """
    
    def __init__(
        self,
        log_dir: str = "audit-logs",
        console_output: bool = True,
        min_severity: AuditSeverity = AuditSeverity.INFO,
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.console_output = console_output
        self.min_severity = min_severity
        self._severity_order = {
            AuditSeverity.INFO: 0,
            AuditSeverity.WARNING: 1,
            AuditSeverity.ERROR: 2,
            AuditSeverity.CRITICAL: 3,
        }
        
        # Set up Python logger for console output
        self._logger = logging.getLogger("audit")
        self._logger.setLevel(logging.INFO)
        
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                "%(asctime)s - AUDIT - %(levelname)s - %(message)s"
            ))
            self._logger.addHandler(handler)
    
    def _should_log(self, severity: AuditSeverity) -> bool:
        """Check if event meets minimum severity threshold."""
        return self._severity_order[severity] >= self._severity_order[self.min_severity]
    
    def _get_log_file(self) -> Path:
        """Get current log file path (rotates daily)."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_dir / f"audit_{date_str}.jsonl"
    
    def log(self, event: AuditEvent) -> None:
        """
        Log an audit event.
        
        Args:
            event: The AuditEvent to log
        """
        if not self._should_log(event.severity):
            return
        
        # Write to file (JSON lines format)
        log_file = self._get_log_file()
        with open(log_file, "a") as f:
            f.write(event.to_json() + "\n")
        
        # Console output
        if self.console_output:
            log_level = {
                AuditSeverity.INFO: logging.INFO,
                AuditSeverity.WARNING: logging.WARNING,
                AuditSeverity.ERROR: logging.ERROR,
                AuditSeverity.CRITICAL: logging.CRITICAL,
            }.get(event.severity, logging.INFO)
            
            self._logger.log(
                log_level,
                f"[{event.event_type.value}] {event.actor}: {event.action} -> {event.outcome}"
            )
    
    def log_authentication(
        self,
        actor: str,
        success: bool,
        ip_address: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log authentication event."""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE,
            category=AuditEventCategory.AUTHENTICATION,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            actor=actor,
            action="User authentication",
            outcome="success" if success else "failure",
            ip_address=ip_address,
            details={"reason": reason} if reason else {},
            **kwargs
        )
        self.log(event)
    
    def log_data_access(
        self,
        actor: str,
        resource_type: str,
        resource_id: str,
        patient_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log data access event."""
        event = AuditEvent(
            event_type=AuditEventType.PHI_ACCESS if patient_id else AuditEventType.PATIENT_READ,
            category=AuditEventCategory.DATA_ACCESS,
            severity=AuditSeverity.INFO,
            actor=actor,
            action=f"Accessed {resource_type}",
            outcome="success",
            resource=resource_id,
            resource_type=resource_type,
            patient_id=patient_id,
            **kwargs
        )
        self.log(event)
    
    def log_access_denied(
        self,
        actor: str,
        resource: str,
        reason: str,
        **kwargs
    ) -> None:
        """Log access denied event."""
        event = AuditEvent(
            event_type=AuditEventType.ACCESS_DENIED,
            category=AuditEventCategory.AUTHORIZATION,
            severity=AuditSeverity.WARNING,
            actor=actor,
            action="Access denied",
            outcome="failure",
            resource=resource,
            details={"reason": reason},
            **kwargs
        )
        self.log(event)
    
    def log_admin_action(
        self,
        actor: str,
        action: str,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Log administrative action."""
        event = AuditEvent(
            event_type=AuditEventType.CONFIG_CHANGED,
            category=AuditEventCategory.ADMIN_ACTION,
            severity=AuditSeverity.WARNING,
            actor=actor,
            action=action,
            outcome="success",
            resource=target,
            details=details or {},
            **kwargs
        )
        self.log(event)
    
    def log_security_event(
        self,
        event_type: AuditEventType,
        actor: str,
        description: str,
        severity: AuditSeverity = AuditSeverity.WARNING,
        **kwargs
    ) -> None:
        """Log security event."""
        event = AuditEvent(
            event_type=event_type,
            category=AuditEventCategory.SECURITY,
            severity=severity,
            actor=actor,
            action=description,
            outcome="detected",
            **kwargs
        )
        self.log(event)
    
    def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query audit events.
        
        Args:
            start_date: Filter events after this date
            end_date: Filter events before this date
            event_type: Filter by event type
            actor: Filter by actor
            limit: Maximum events to return
        
        Returns:
            List of matching audit events
        """
        events = []
        
        # Find relevant log files
        for log_file in sorted(self.log_dir.glob("audit_*.jsonl"), reverse=True):
            with open(log_file, "r") as f:
                for line in f:
                    if len(events) >= limit:
                        break
                    
                    try:
                        event = json.loads(line)
                        
                        # Apply filters
                        if event_type and event.get("event_type") != event_type.value:
                            continue
                        if actor and event.get("actor") != actor:
                            continue
                        
                        event_time = datetime.fromisoformat(event.get("timestamp", ""))
                        if start_date and event_time < start_date:
                            continue
                        if end_date and event_time > end_date:
                            continue
                        
                        events.append(event)
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            if len(events) >= limit:
                break
        
        return events


# Global singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(
            log_dir=os.getenv("AUDIT_LOG_DIR", "audit-logs"),
            console_output=os.getenv("AUDIT_CONSOLE_OUTPUT", "true").lower() == "true",
        )
    return _audit_logger


def audit_log(event: AuditEvent) -> None:
    """Convenience function to log an audit event."""
    get_audit_logger().log(event)
