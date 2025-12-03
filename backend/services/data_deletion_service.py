"""
Data deletion service for GDPR right to be forgotten.

Handles user data deletion requests in compliance with regional policies.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import (
    AnalysisHistory,
    Document,
    OCRExtraction,
    UserSession,
    Consent,
    TwoFactorAuth,
)
from backend.database.connection import get_db_session
from backend.config.compliance_policies import (
    get_compliance_policy,
    get_region,
    is_data_deletion_allowed,
)

logger = logging.getLogger(__name__)


class DataDeletionService:
    """Service for handling GDPR data deletion requests."""
    
    def __init__(self):
        """Initialize data deletion service."""
        self.region = get_region()
        self.policy = get_compliance_policy()
    
    async def delete_user_data(
        self,
        user_id: str,
        patient_id: Optional[str] = None,
        delete_audit_logs: bool = False,
    ) -> Dict[str, Any]:
        """
        Delete all user data (GDPR right to be forgotten).
        
        Args:
            user_id: User ID whose data should be deleted
            patient_id: Optional patient ID (if user is a patient)
            delete_audit_logs: Whether to delete audit logs (may be required for compliance)
            
        Returns:
            Dictionary with deletion summary
        """
        if not is_data_deletion_allowed():
            raise ValueError(
                f"Data deletion is not allowed in region {self.region}"
            )
        
        deletion_summary = {
            "user_id": user_id,
            "region": self.region,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "items_deleted": {},
        }
        
        async with get_db_session() as session:
            # Delete analysis history
            analysis_count = await self._delete_analysis_history(
                session, user_id, patient_id
            )
            deletion_summary["items_deleted"]["analysis_history"] = analysis_count
            
            # Delete documents (if patient_id provided)
            if patient_id:
                document_count = await self._delete_documents(
                    session, patient_id
                )
                deletion_summary["items_deleted"]["documents"] = document_count
            
            # Delete user sessions
            session_count = await self._delete_user_sessions(
                session, user_id
            )
            deletion_summary["items_deleted"]["user_sessions"] = session_count
            
            # Delete consents (withdraw all)
            consent_count = await self._withdraw_all_consents(
                session, user_id
            )
            deletion_summary["items_deleted"]["consents_withdrawn"] = consent_count
            
            # Delete 2FA records
            twofa_deleted = await self._delete_2fa(session, user_id)
            deletion_summary["items_deleted"]["two_factor_auth"] = twofa_deleted
            
            # Optionally delete audit logs (may be required by policy)
            if delete_audit_logs or not self.policy.retain_logs:
                audit_count = await self._delete_audit_logs(
                    session, user_id, patient_id
                )
                deletion_summary["items_deleted"]["audit_logs"] = audit_count
            else:
                deletion_summary["items_deleted"]["audit_logs"] = 0
                deletion_summary["note"] = "Audit logs retained per compliance policy"
            
            await session.commit()
        
        logger.info(
            f"Data deletion completed for user {user_id} in region {self.region}",
            extra={"deletion_summary": deletion_summary}
        )
        
        return deletion_summary
    
    async def _delete_analysis_history(
        self,
        session: AsyncSession,
        user_id: str,
        patient_id: Optional[str] = None,
    ) -> int:
        """Delete analysis history for user/patient."""
        query = delete(AnalysisHistory).where(
            AnalysisHistory.user_id == user_id
        )
        if patient_id:
            query = query.where(AnalysisHistory.patient_id == patient_id)
        
        result = await session.execute(query)
        return result.rowcount
    
    async def _delete_documents(
        self,
        session: AsyncSession,
        patient_id: str,
    ) -> int:
        """Delete documents for a patient."""
        query = delete(Document).where(
            Document.patient_id == patient_id
        )
        result = await session.execute(query)
        return result.rowcount
    
    async def _delete_user_sessions(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> int:
        """Delete all user sessions."""
        query = delete(UserSession).where(
            UserSession.user_id == user_id
        )
        result = await session.execute(query)
        return result.rowcount
    
    async def _withdraw_all_consents(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> int:
        """Withdraw all user consents."""
        stmt = select(Consent).where(
            and_(
                Consent.user_id == user_id,
                Consent.accepted == 1
            )
        )
        result = await session.execute(stmt)
        consents = result.scalars().all()
        
        count = 0
        for consent in consents:
            consent.accepted = 0
            consent.withdrawn_at = datetime.now(timezone.utc)
            count += 1
        
        return count
    
    async def _delete_2fa(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> bool:
        """Delete 2FA records for user."""
        query = delete(TwoFactorAuth).where(
            TwoFactorAuth.user_id == user_id
        )
        result = await session.execute(query)
        return result.rowcount > 0
    
    async def _delete_audit_logs(
        self,
        session: AsyncSession,
        user_id: str,
        patient_id: Optional[str] = None,
    ) -> int:
        """Delete audit logs for user/patient."""
        from backend.database.models import AuditLog
        
        query = delete(AuditLog).where(
            AuditLog.user_id == user_id
        )
        if patient_id:
            query = query.where(AuditLog.patient_id == patient_id)
        
        result = await session.execute(query)
        return result.rowcount
    
    async def get_deletion_status(
        self,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get status of data deletion for a user.
        
        Returns information about what data exists and can be deleted.
        """
        async with get_db_session() as session:
            # Count analysis history
            analysis_stmt = select(AnalysisHistory).where(
                AnalysisHistory.user_id == user_id
            )
            analysis_result = await session.execute(analysis_stmt)
            analysis_count = len(analysis_result.scalars().all())
            
            # Count user sessions
            from backend.database.models import UserSession
            try:
                session_stmt = select(UserSession).where(
                    UserSession.user_id == user_id
                )
                session_result = await session.execute(session_stmt)
                session_count = len(session_result.scalars().all())
            except Exception as e:
                # Handle case where session_metadata column doesn't exist yet
                logger.warning(f"Error counting user sessions: {e}")
                session_count = 0
            
            # Count consents
            consent_stmt = select(Consent).where(
                Consent.user_id == user_id
            )
            consent_result = await session.execute(consent_stmt)
            consent_count = len(consent_result.scalars().all())
            
            # Check 2FA
            twofa_stmt = select(TwoFactorAuth).where(
                TwoFactorAuth.user_id == user_id
            )
            twofa_result = await session.execute(twofa_stmt)
            has_2fa = twofa_result.scalar_one_or_none() is not None
        
        return {
            "user_id": user_id,
            "region": self.region,
            "data_deletion_allowed": is_data_deletion_allowed(),
            "data_summary": {
                "analysis_history_count": analysis_count,
                "user_sessions_count": session_count,
                "consents_count": consent_count,
                "has_2fa": has_2fa,
            },
        }
