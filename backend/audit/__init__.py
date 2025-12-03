"""
Audit Module
SOC 2 compliant audit logging infrastructure.
"""

from .audit_events import (
    AuditEvent,
    AuditEventType,
    AuditEventCategory,
    AuditSeverity,
    login_success,
    login_failure,
    access_denied,
    phi_access,
    config_changed,
)

from .audit_logger import (
    AuditLogger,
    get_audit_logger,
    audit_log,
)

from .audit_middleware import AuditMiddleware

__all__ = [
    # Event types
    "AuditEvent",
    "AuditEventType",
    "AuditEventCategory",
    "AuditSeverity",
    # Event builders
    "login_success",
    "login_failure",
    "access_denied",
    "phi_access",
    "config_changed",
    # Logger
    "AuditLogger",
    "get_audit_logger",
    "audit_log",
    # Middleware
    "AuditMiddleware",
]
