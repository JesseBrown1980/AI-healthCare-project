"""
Audit Event Definitions
Standardized event types for security and compliance audit logging.
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class AuditEventCategory(str, Enum):
    """Categories of audit events."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    ADMIN_ACTION = "admin_action"
    SYSTEM = "system"
    SECURITY = "security"


class AuditEventType(str, Enum):
    """Specific audit event types."""
    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    TOKEN_ISSUED = "auth.token.issued"
    TOKEN_REVOKED = "auth.token.revoked"
    TOKEN_EXPIRED = "auth.token.expired"
    MFA_SUCCESS = "auth.mfa.success"
    MFA_FAILURE = "auth.mfa.failure"
    
    # Authorization events
    ACCESS_GRANTED = "authz.access.granted"
    ACCESS_DENIED = "authz.access.denied"
    PRIVILEGE_ESCALATION = "authz.privilege.escalation"
    SCOPE_VIOLATION = "authz.scope.violation"
    
    # Data access events
    PATIENT_READ = "data.patient.read"
    PATIENT_SEARCH = "data.patient.search"
    PHI_ACCESS = "data.phi.access"
    REPORT_GENERATED = "data.report.generated"
    DATA_EXPORT = "data.export"
    
    # Data modification events
    PATIENT_CREATE = "data.patient.create"
    PATIENT_UPDATE = "data.patient.update"
    PATIENT_DELETE = "data.patient.delete"
    ANALYSIS_CREATED = "data.analysis.created"
    
    # Admin events
    USER_CREATED = "admin.user.created"
    USER_UPDATED = "admin.user.updated"
    USER_DELETED = "admin.user.deleted"
    ROLE_ASSIGNED = "admin.role.assigned"
    ROLE_REVOKED = "admin.role.revoked"
    CONFIG_CHANGED = "admin.config.changed"
    
    # System events
    SERVICE_START = "system.service.start"
    SERVICE_STOP = "system.service.stop"
    DEPLOYMENT = "system.deployment"
    ERROR = "system.error"
    
    # Security events
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    RATE_LIMIT_EXCEEDED = "security.ratelimit"
    INVALID_TOKEN = "security.token.invalid"
    BRUTE_FORCE_DETECTED = "security.bruteforce"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """
    Structured audit event for SOC 2 compliance.
    
    Attributes:
        event_type: Type of event (from AuditEventType)
        category: Category of event (from AuditEventCategory)
        severity: Severity level
        actor: Who performed the action (user ID, service name)
        resource: What was accessed/modified
        action: What was done
        outcome: Success or failure
        details: Additional context
    """
    event_type: AuditEventType
    category: AuditEventCategory
    severity: AuditSeverity
    actor: str
    action: str
    outcome: str
    
    # Optional fields
    resource: Optional[str] = None
    resource_type: Optional[str] = None
    patient_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Auto-generated fields
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: "")
    
    def __post_init__(self):
        import uuid
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "actor": self.actor,
            "action": self.action,
            "outcome": self.outcome,
            "resource": self.resource,
            "resource_type": self.resource_type,
            "patient_id": self.patient_id,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "details": self.details,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict())


# Pre-defined event builders for common scenarios
def login_success(actor: str, ip_address: str = None, **kwargs) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.LOGIN_SUCCESS,
        category=AuditEventCategory.AUTHENTICATION,
        severity=AuditSeverity.INFO,
        actor=actor,
        action="User logged in",
        outcome="success",
        ip_address=ip_address,
        **kwargs
    )


def login_failure(actor: str, reason: str, ip_address: str = None, **kwargs) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.LOGIN_FAILURE,
        category=AuditEventCategory.AUTHENTICATION,
        severity=AuditSeverity.WARNING,
        actor=actor,
        action="Login attempt failed",
        outcome="failure",
        ip_address=ip_address,
        details={"reason": reason},
        **kwargs
    )


def access_denied(actor: str, resource: str, reason: str, **kwargs) -> AuditEvent:
    return AuditEvent(
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


def phi_access(actor: str, patient_id: str, resource_type: str, **kwargs) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.PHI_ACCESS,
        category=AuditEventCategory.DATA_ACCESS,
        severity=AuditSeverity.INFO,
        actor=actor,
        action=f"Accessed {resource_type}",
        outcome="success",
        patient_id=patient_id,
        resource_type=resource_type,
        **kwargs
    )


def config_changed(actor: str, setting: str, old_value: str, new_value: str, **kwargs) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.CONFIG_CHANGED,
        category=AuditEventCategory.ADMIN_ACTION,
        severity=AuditSeverity.WARNING,
        actor=actor,
        action=f"Changed configuration: {setting}",
        outcome="success",
        details={"setting": setting, "old_value": old_value, "new_value": new_value},
        **kwargs
    )
