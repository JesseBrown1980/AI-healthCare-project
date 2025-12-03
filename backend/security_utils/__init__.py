"""
Security Module
HIPAA-compliant security utilities for PHI protection.
"""

from .phi_filter import (
    PHIFilter,
    PHIType,
    PHIMatch,
    redact_phi,
    contains_phi,
    get_phi_filter,
)

from .log_sanitizer import (
    SecureLogger,
    SanitizingFormatter,
    get_secure_logger,
    sanitize_dict,
    log_sanitized,
    configure_secure_logging,
)

from .session_manager import (
    Session,
    SessionManager,
    get_session_manager,
)

from .data_retention import (
    RetentionPolicy,
    DataRetentionService,
    get_retention_service,
    run_scheduled_cleanup,
)

__all__ = [
    # PHI Filter
    "PHIFilter",
    "PHIType",
    "PHIMatch",
    "redact_phi",
    "contains_phi",
    "get_phi_filter",
    # Log Sanitizer
    "SecureLogger",
    "SanitizingFormatter",
    "get_secure_logger",
    "sanitize_dict",
    "log_sanitized",
    "configure_secure_logging",
    # Session Manager
    "Session",
    "SessionManager",
    "get_session_manager",
    # Data Retention
    "RetentionPolicy",
    "DataRetentionService",
    "get_retention_service",
    "run_scheduled_cleanup",
]

