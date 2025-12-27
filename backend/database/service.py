"""
Database service layer for Healthcare AI Assistant.

Provides high-level database operations with Redis caching.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import get_db_session, get_redis_client
from .models import AnalysisHistory, Document, OCRExtraction, UserSession, AuditLog

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations with Redis caching."""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.cache_ttl = 300  # 5 minutes default
    
    # ==================== Analysis History ====================
    
    async def save_analysis(
        self,
        patient_id: str,
        analysis_data: Dict[str, Any],
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """Save analysis to database."""
        async with get_db_session() as session:
            analysis = AnalysisHistory(
                id=str(uuid4()),
                patient_id=patient_id,
                analysis_timestamp=datetime.now(timezone.utc),
                analysis_data=analysis_data.get("analysis_data"),
                risk_scores=analysis_data.get("risk_scores"),
                alerts=analysis_data.get("alerts"),
                recommendations=analysis_data.get("recommendations"),
                user_id=user_id,
                correlation_id=correlation_id,
            )
            session.add(analysis)
            await session.flush()
            analysis_id = analysis.id
            
            # Invalidate cache
            if self.redis_client:
                await self.redis_client.delete(f"patient:analysis:{patient_id}:latest")
                await self.redis_client.delete(f"patient:summary:{patient_id}")
            
            return analysis_id
    
    async def get_latest_analysis(
        self,
        patient_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get latest analysis for a patient with caching.
        
        Returns analysis in the same format as in-memory storage for compatibility.
        """
        # Try cache first
        if self.redis_client:
            cached = await self.redis_client.get(f"patient:analysis:{patient_id}:latest")
            if cached:
                return json.loads(cached)
        
        # Query database
        async with get_db_session() as session:
            result = await session.execute(
                select(AnalysisHistory)
                .where(AnalysisHistory.patient_id == patient_id)
                .order_by(desc(AnalysisHistory.analysis_timestamp))
                .limit(1)
            )
            analysis = result.scalar_one_or_none()
            
            if not analysis:
                return None
            
            # Extract the nested analysis_data (which contains the full original analysis)
            nested_analysis = analysis.analysis_data or {}
            
            # Reconstruct the flat structure expected by the rest of the codebase
            # This matches the in-memory format from PatientAnalyzer.analyze()
            data = {
                # Top-level fields from nested analysis
                "patient_id": nested_analysis.get("patient_id") or analysis.patient_id,
                "patient_data": nested_analysis.get("patient_data"),
                "last_analyzed_at": nested_analysis.get("last_analyzed_at") or analysis.analysis_timestamp.isoformat(),
                "analysis_timestamp": nested_analysis.get("analysis_timestamp") or analysis.analysis_timestamp.isoformat(),
                "status": nested_analysis.get("status", "completed"),
                "summary": nested_analysis.get("summary"),
                "alert_count": nested_analysis.get("alert_count"),
                "highest_alert_severity": nested_analysis.get("highest_alert_severity"),
                "overall_risk_score": nested_analysis.get("overall_risk_score"),
                "polypharmacy_risk": nested_analysis.get("polypharmacy_risk"),
                "medication_review": nested_analysis.get("medication_review"),
                "active_specialties": nested_analysis.get("active_specialties"),
                "analysis_duration_seconds": nested_analysis.get("analysis_duration_seconds"),
                # Fields that were stored separately in database
                "risk_scores": analysis.risk_scores or nested_analysis.get("risk_scores", {}),
                "alerts": analysis.alerts or nested_analysis.get("alerts", []),
                "recommendations": analysis.recommendations or nested_analysis.get("recommendations", []),
                # Metadata
                "user_id": analysis.user_id or nested_analysis.get("user_id"),
                "correlation_id": analysis.correlation_id or nested_analysis.get("correlation_id"),
            }
            
            # Cache result
            if self.redis_client:
                await self.redis_client.setex(
                    f"patient:analysis:{patient_id}:latest",
                    self.cache_ttl,
                    json.dumps(data, default=str),
                )
            
            return data
    
    async def get_analysis_history(
        self,
        patient_id: str,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Get analysis history for a patient."""
        async with get_db_session() as session:
            result = await session.execute(
                select(AnalysisHistory)
                .where(AnalysisHistory.patient_id == patient_id)
                .order_by(desc(AnalysisHistory.analysis_timestamp))
                .limit(limit)
            )
            analyses = result.scalars().all()
            
            return [
                {
                    "id": str(analysis.id),
                    "patient_id": analysis.patient_id,
                    "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
                    "risk_scores": analysis.risk_scores,
                    "alerts": analysis.alerts,
                    "user_id": analysis.user_id,
                }
                for analysis in analyses
            ]
    
    async def cleanup_old_analyses(
        self,
        patient_id: Optional[str] = None,
        days_to_keep: int = 90,
    ) -> int:
        """Clean up old analyses beyond retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        async with get_db_session() as session:
            query = delete(AnalysisHistory).where(
                AnalysisHistory.analysis_timestamp < cutoff
            )
            if patient_id:
                query = query.where(AnalysisHistory.patient_id == patient_id)
            
            result = await session.execute(query)
            await session.commit()
            return result.rowcount
    
    # ==================== Cache Operations ====================
    
    async def cache_patient_summary(
        self,
        patient_id: str,
        summary: Dict[str, Any],
        ttl: int = 300,
    ) -> None:
        """Cache patient summary in Redis."""
        if not self.redis_client:
            return
        
        await self.redis_client.setex(
            f"patient:summary:{patient_id}",
            ttl,
            json.dumps(summary, default=str),
        )
    
    async def get_cached_summary(
        self,
        patient_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get cached patient summary."""
        if not self.redis_client:
            return None
        
        cached = await self.redis_client.get(f"patient:summary:{patient_id}")
        if cached:
            return json.loads(cached)
        return None
    
    async def clear_cache(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching pattern."""
        if not self.redis_client:
            return 0
        
        if pattern:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
        else:
            # Clear all cache keys (be careful!)
            keys = await self.redis_client.keys("patient:*")
            if keys:
                return await self.redis_client.delete(*keys)
        return 0
    
    # ==================== Audit Logging ====================
    
    async def log_audit_event(
        self,
        correlation_id: str,
        user_id: Optional[str],
        patient_id: Optional[str],
        action: str,
        resource_type: str,
        outcome: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log an audit event."""
        async with get_db_session() as session:
            audit_log = AuditLog(
                id=str(uuid4()),
                correlation_id=correlation_id,
                user_id=user_id,
                patient_id=patient_id,
                action=action,
                resource_type=resource_type,
                outcome=outcome,
                timestamp=datetime.now(timezone.utc),
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
            )
            session.add(audit_log)
            await session.flush()
            return audit_log.id
    
    # ==================== Document Management ====================
    
    async def save_document(self, document_data: Dict[str, Any]) -> str:
        """Save a document record."""
        async with get_db_session() as session:
            document = Document(
                id=document_data["id"],
                patient_id=document_data.get("patient_id"),
                document_type=document_data.get("document_type"),
                file_path=document_data["file_path"],
                file_hash=document_data["file_hash"],
                uploaded_at=document_data.get("uploaded_at", datetime.now(timezone.utc)),
                created_by=document_data.get("created_by"),
            )
            session.add(document)
            await session.flush()
            return document.id
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                return None
            
            return {
                "id": document.id,
                "patient_id": document.patient_id,
                "document_type": document.document_type,
                "file_path": document.file_path,
                "file_hash": document.file_hash,
                "ocr_text": document.ocr_text,
                "ocr_confidence": document.ocr_confidence,
                "extracted_data": document.extracted_data,
                "fhir_resource_id": document.fhir_resource_id,
                "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
                "processed_at": document.processed_at.isoformat() if document.processed_at else None,
                "created_by": document.created_by,
            }
    
    async def get_document_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get a document by file hash (for duplicate detection)."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Document).where(Document.file_hash == file_hash)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                return None
            
            return {
                "id": document.id,
                "file_path": document.file_path,
                "file_hash": document.file_hash,
            }
    
    async def update_document(
        self,
        document_id: str,
        updates: Dict[str, Any],
    ) -> None:
        """Update a document record."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            for key, value in updates.items():
                if hasattr(document, key):
                    setattr(document, key, value)
            
            await session.flush()
    
    async def get_patient_documents(
        self,
        patient_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get all documents for a patient."""
        async with get_db_session() as session:
            result = await session.execute(
                select(Document)
                .where(Document.patient_id == patient_id)
                .order_by(desc(Document.uploaded_at))
                .limit(limit)
            )
            documents = result.scalars().all()
            
            return [
                {
                    "id": doc.id,
                    "document_type": doc.document_type,
                    "file_path": doc.file_path,
                    "ocr_text": doc.ocr_text,
                    "ocr_confidence": doc.ocr_confidence,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
                }
                for doc in documents
            ]
    
    async def save_ocr_extraction(self, ocr_data: Dict[str, Any]) -> str:
        """Save OCR extraction result.
        
        Note: The OCRExtraction model is designed for structured extractions
        (lab values, medications, etc.). The raw OCR text is stored in Document.ocr_text.
        This method can be used for future structured extractions.
        """
        async with get_db_session() as session:
            extraction = OCRExtraction(
                id=str(uuid4()),
                document_id=ocr_data["document_id"],
                extraction_type=ocr_data.get("extraction_type", "raw_text"),
                field_name=ocr_data.get("field_name", "full_text"),
                extracted_value=ocr_data.get("extracted_text", ""),
                confidence=ocr_data.get("confidence", 0.0),
                normalized_value=ocr_data.get("metadata"),
            )
            session.add(extraction)
            await session.flush()
            return extraction.id
    
    async def get_ocr_fhir_resources_for_patient(
        self,
        patient_id: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all FHIR resources extracted from OCR documents for a patient.
        
        Converts parsed_data from documents to FHIR resources on-the-fly.
        
        Returns a dictionary with keys: 'observations', 'medication_statements', 'conditions'
        containing lists of FHIR resources.
        """
        async with get_db_session() as session:
            # Get all processed documents for this patient with parsed data
            result = await session.execute(
                select(Document)
                .where(Document.patient_id == patient_id)
                .where(Document.extracted_data.isnot(None))
                .order_by(desc(Document.processed_at))
            )
            documents = result.scalars().all()
            
            if not documents:
                return {
                    "observations": [],
                    "medication_statements": [],
                    "conditions": [],
                }
            
            # Import FHIR mapper to convert parsed_data to FHIR
            from backend.ocr.fhir_mapper import FHIRMapper
            fhir_mapper = FHIRMapper()
            
            # Collect FHIR resources from all documents
            observations = []
            medication_statements = []
            conditions = []
            
            for doc in documents:
                extracted_data = doc.extracted_data or {}
                
                # Convert parsed_data to FHIR resources
                try:
                    fhir_resources = fhir_mapper.map_parsed_data_to_fhir(
                        parsed_data=extracted_data,
                        patient_id=patient_id,
                        document_id=doc.id,
                    )
                    
                    observations.extend(fhir_resources.get("observations", []))
                    medication_statements.extend(fhir_resources.get("medication_statements", []))
                    conditions.extend(fhir_resources.get("conditions", []))
                except Exception as e:
                    logger.warning(
                        "Failed to convert OCR data to FHIR for document %s: %s", doc.id, str(e)
                    )
                    continue
            
            return {
                "observations": observations,
                "medication_statements": medication_statements,
                "conditions": conditions,
            }

