"""
SQLAlchemy models for Healthcare AI Assistant database.
"""

from datetime import datetime
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
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
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
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
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
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
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
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="ocr_extractions")


class UserSession(Base):
    """Store user session data."""
    
    __tablename__ = "user_sessions"
    
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    token_hash = Column(String(255))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_activity = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    metadata = Column(JSONColumn())


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
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    details = Column(JSONColumn())
    
    __table_args__ = (
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_patient_timestamp", "patient_id", "timestamp"),
    )

