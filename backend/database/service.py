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
        """Get latest analysis for a patient with caching."""
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
            
            data = {
                "patient_id": analysis.patient_id,
                "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
                "analysis_data": analysis.analysis_data,
                "risk_scores": analysis.risk_scores,
                "alerts": analysis.alerts,
                "recommendations": analysis.recommendations,
                "user_id": analysis.user_id,
                "correlation_id": analysis.correlation_id,
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

