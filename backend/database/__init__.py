"""
Database module for Healthcare AI Assistant.

Provides database connection management, models, and services.
"""

from .connection import get_db_session, get_redis_client, init_database, close_database
from .models import (
    Base, AnalysisHistory, Document, OCRExtraction, UserSession, AuditLog, Consent, TwoFactorAuth,
    PatientMedication, CareTeamMember, PatientProfile
)
from .service import DatabaseService

__all__ = [
    "get_db_session",
    "get_redis_client",
    "init_database",
    "close_database",
    "DatabaseService",
    "Base",
    "AnalysisHistory",
    "Document",
    "OCRExtraction",
    "UserSession",
    "AuditLog",
    "Consent",
    "TwoFactorAuth",
    "PatientMedication",
    "CareTeamMember",
    "PatientProfile",
]

