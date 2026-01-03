"""
SQLAlchemy models for Healthcare AI Assistant database.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
# UUID, JSONB, INET imported but not used - keeping for future PostgreSQL-specific features
# from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

Base = declarative_base()

# Use JSONB for PostgreSQL, JSON for SQLite
# We'll use JSON for compatibility - PostgreSQL will handle it efficiently
JSONColumn = JSON


class AnalysisHistory(Base):
    """Store patient analysis history."""
    
    __tablename__ = "analysis_history"
    
    id = Column(String(36), primary_key=True)
    patient_id = Column(String(255), nullable=False, index=True)
    analysis_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    analysis_data = Column(JSONColumn())  # Full analysis result
    risk_scores = Column(JSONColumn())
    alerts = Column(JSONColumn())
    recommendations = Column(JSONColumn())
    user_id = Column(String(255), index=True)
    correlation_id = Column(String(255), index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_analysis_patient_timestamp", "patient_id", "analysis_timestamp"),
    )


class Document(Base):
    """Store uploaded documents (for future OCR integration)."""
    
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True)
    patient_id = Column(String(255), index=True)
    document_type = Column(String(50))  # 'lab_result', 'prescription', 'note', etc.
    file_path = Column(Text)
    file_hash = Column(String(64), unique=True, index=True)  # For deduplication
    ocr_text = Column(Text)
    ocr_confidence = Column(Float)
    extracted_data = Column(JSONColumn())  # Structured extracted data
    fhir_resource_id = Column(String(255))
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    processed_at = Column(DateTime(timezone=True))
    created_by = Column(String(255))
    
    # Relationships
    ocr_extractions = relationship("OCRExtraction", back_populates="document", cascade="all, delete-orphan")


class OCRExtraction(Base):
    """Store OCR extraction results (for future OCR integration)."""
    
    __tablename__ = "ocr_extractions"
    
    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    extraction_type = Column(String(50))  # 'lab_value', 'medication', 'vital_sign'
    field_name = Column(String(100))
    extracted_value = Column(Text)
    confidence = Column(Float)
    normalized_value = Column(JSONColumn())  # FHIR-compatible format
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    document = relationship("Document", back_populates="ocr_extractions")


class User(Base):
    """Store user account information with authentication credentials."""
    
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # bcrypt hashed password (null for OAuth-only users)
    full_name = Column(String(255))
    roles = Column(JSONColumn())  # List of roles: ['admin', 'clinician', 'viewer']
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    is_verified = Column(Integer, default=0)  # Email verification status
    verification_token = Column(String(255))  # Email verification token
    verification_token_expires = Column(DateTime(timezone=True))  # Token expiration
    password_reset_token = Column(String(255))  # Password reset token
    password_reset_token_expires = Column(DateTime(timezone=True))  # Reset token expiration
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    last_login = Column(DateTime(timezone=True))
    user_metadata = Column(JSONColumn())  # Additional user metadata
    
    # OAuth provider fields
    oauth_provider = Column(String(50), nullable=True, index=True)  # 'google', 'apple', or None for password auth
    oauth_provider_id = Column(String(255), nullable=True, index=True)  # Provider's user ID (sub claim)
    oauth_access_token = Column(Text, nullable=True)  # Encrypted OAuth access token
    oauth_refresh_token = Column(Text, nullable=True)  # Encrypted OAuth refresh token
    oauth_token_expires = Column(DateTime(timezone=True), nullable=True)  # Token expiration
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """Store user session data."""
    
    __tablename__ = "user_sessions"
    
    session_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_activity = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    session_metadata = Column(JSONColumn())
    
    # Relationships
    user = relationship("User", back_populates="sessions")


class AuditLog(Base):
    """Store audit logs for HIPAA compliance."""
    
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    correlation_id = Column(String(255), index=True)
    user_id = Column(String(255), index=True)
    patient_id = Column(String(255), index=True)
    action = Column(String(50))  # 'READ', 'WRITE', 'DELETE'
    resource_type = Column(String(50))
    outcome = Column(String(10))  # '0' success, '8' error
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    details = Column(JSONColumn())
    
    __table_args__ = (
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_patient_timestamp", "patient_id", "timestamp"),
    )


class Consent(Base):
    """Store user consent records for GDPR and regional compliance."""
    
    __tablename__ = "consents"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    consent_type = Column(String(50), nullable=False)  # 'privacy_policy', 'terms_of_service', 'data_processing', etc.
    version = Column(String(50))  # Version of the policy/terms
    accepted = Column(Integer, default=1)  # 1 = accepted, 0 = withdrawn
    accepted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45))  # IP address when consent was given/withdrawn
    user_agent = Column(Text)  # User agent when consent was given/withdrawn
    metadata = Column(JSONColumn())  # Additional metadata (e.g., consent method, language)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index("idx_consent_user_type", "user_id", "consent_type"),
        Index("idx_consent_user_accepted", "user_id", "accepted"),
    )

