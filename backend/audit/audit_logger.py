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

# Import Compliance Service
from backend.compliance_service import ComplianceService

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
        compliance_service: Optional[ComplianceService] = None,
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.console_output = console_output
        self.min_severity = min_severity
        self.compliance_service = compliance_service or ComplianceService()
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
        Log an audit event with Crypto-Shredding for PII.
        
        Args:
            event: The AuditEvent to log
        """
        if not self._should_log(event.severity):
            return
            
        event_dict = event.to_dict()
        
        # CRYPTO-SHREDDING: Encrypt sensitive PII in the persistent log
        # We assume 'actor' and 'patient_id' are the primary entities to protect.
        
        # 1. Encrypt 'actor' (User ID)
        if event_dict.get("actor"):
            event_dict["actor"] = self.compliance_service.shred_data(
                event_dict["actor"], entity_id=event_dict["actor"]
            )
            
        # 2. Encrypt 'patient_id'
        if event_dict.get("patient_id"):
            event_dict["patient_id"] = self.compliance_service.shred_data(
                event_dict["patient_id"], entity_id=event_dict["patient_id"]
            )
            
        # 3. Encrypt IP Address (Linked to Actor)
        # We use the actor's ID as the key for the IP if the actor is known,
        # otherwise we might leave it or use a system key. For now, use actor ID if present.
        if event_dict.get("ip_address") and event.actor:
             event_dict["ip_address"] = self.compliance_service.shred_data(
                event_dict["ip_address"], entity_id=event.actor
            )

        # Write encrypted dict to file (JSON lines format)
        log_file = self._get_log_file()
        with open(log_file, "a") as f:
            f.write(json.dumps(event_dict) + "\n")
        
        # Console output (Keep readable for dev/ops - OR mask it? 
        # Standard practice: Mask PII in console logs, Encrypt in audit logs.
        # For this PoC, we will just log the readable version to console for debugging,
        # effectively handling console as ephemeral/secure environment).
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

    # Legacy wrappers delegated to internal logic...
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
        Query audit events with automatic decryption.
        """
        events = []
        
        # Find relevant log files
        for log_file in sorted(self.log_dir.glob("audit_*.jsonl"), reverse=True):
            if not log_file.exists(): continue
            
            with open(log_file, "r") as f:
                for line in f:
                    if len(events) >= limit:
                        break
                    
                    try:
                        event_dict = json.loads(line)
                        
                        # DECRYPTION: Attempt to restore PII
                        # Note: If actor ID is encrypted, we can't filter by actor easily without decrypting all.
                        # For efficiency in a real DB, we'd index on a hashed actors, but for JSONL we scan.
                        
                        if event_dict.get("actor"):
                            event_dict["actor"] = self.compliance_service.unshred_data(event_dict["actor"])
                            
                        if event_dict.get("patient_id"):
                            event_dict["patient_id"] = self.compliance_service.unshred_data(event_dict["patient_id"])
                            
                        if event_dict.get("ip_address"):
                             event_dict["ip_address"] = self.compliance_service.unshred_data(event_dict["ip_address"])

                        # Apply filters
                        if event_type and event_dict.get("event_type") != event_type.value:
                            continue
                        if actor and event_dict.get("actor") != actor:
                            continue
                        
                        event_time = datetime.fromisoformat(event_dict.get("timestamp", ""))
                        if start_date and event_time < start_date:
                            continue
                        if end_date and event_time > end_date:
                            continue
                        
                        events.append(event_dict)
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
