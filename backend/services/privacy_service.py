
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database.models import (
    User, AnalysisHistory, Document, PatientProfile, 
    PatientMedication, CareTeamMember, Consent, UserSession, AuditLog
)

logger = logging.getLogger(__name__)

class PrivacyService:
    """
    Service for handling data privacy requests (GDPR/HIPAA).
    Implements 'Right to be Forgotten' and Data Portability.
    """

    async def delete_user_data(self, session: AsyncSession, user_id: str, soft_delete: bool = False) -> Dict[str, int]:
        """
        Permanently delete all data associated with a user (Right to be Forgotten).
        
        Args:
            session: Database session
            user_id: ID of the user request deletion
            soft_delete: If True, only marks data as deleted (not implemented here, strict GDPR usually implies hard delete)
            
        Returns:
            Dict showing count of deleted records per entity
        """
        logger.info(f"Initiating GDPR data deletion for user {user_id}")
        
        deleted_counts = {}

        try:
            # 1. Delete Clinical Data (Patient Profile, Meds, Team)
            # Find patient profile to get patient_id if needed, but models link by user_id too
            result = await session.execute(select(PatientProfile).where(PatientProfile.user_id == user_id))
            profile = result.scalars().first()
            patient_id = profile.patient_id if profile else None

            # Delete Profile
            if profile:
                await session.delete(profile)
                deleted_counts["patient_profiles"] = 1
            
            # Delete Medications
            result = await session.execute(delete(PatientMedication).where(PatientMedication.user_id == user_id))
            deleted_counts["patient_medications"] = result.rowcount
            
            # Delete Care Team
            result = await session.execute(delete(CareTeamMember).where(CareTeamMember.user_id == user_id))
            deleted_counts["care_team_members"] = result.rowcount

            # 2. Delete Analysis History
            result = await session.execute(delete(AnalysisHistory).where(AnalysisHistory.user_id == user_id))
            deleted_counts["analysis_history"] = result.rowcount

            # 3. Delete Documents 
            # Note: In a real system, this should also trigger file system/S3 deletion
            # For this implementation, we just delete the DB records
            # If patient_id was found, delete documents for that patient that were uploaded by this user?
            # Document model has `created_by`? Let's check model. 
            # Document has `patient_id` and `created_by`. 
            # We'll delete documents created by this user.
            result = await session.execute(delete(Document).where(Document.created_by == user_id))
            deleted_counts["documents"] = result.rowcount

            # 4. Delete Consents
            result = await session.execute(delete(Consent).where(Consent.user_id == user_id))
            deleted_counts["consents"] = result.rowcount

            # 5. Delete User Sessions
            result = await session.execute(delete(UserSession).where(UserSession.user_id == user_id))
            deleted_counts["sessions"] = result.rowcount

            # 6. Delete User Account
            result = await session.execute(delete(User).where(User.id == user_id))
            deleted_counts["users"] = result.rowcount
            
            # 7. Audit Logs - DO NOT DELETE, but we could anonymize if needed.
            # Standard practice is to keep security logs. We will log the deletion event itself in the calling controller.
            
            # CRYPTO-SHREDDING: Destroy compliance keys
            # This renders 'actor' and 'patient_id' in legacy logs unreadable.
            from backend.compliance_service import ComplianceService
            try:
                compliance_svc = ComplianceService()
                compliance_svc.delete_key(user_id)
                # If there is a separate patient_id linked, we should delete that too if it's 1:1
                if patient_id:
                    compliance_svc.delete_key(patient_id)
                logger.info(f"Crypto-shredded compliance keys for user {user_id}")
            except Exception as cs_err:
                logger.error(f"Failed to crypto-shred keys for {user_id}: {cs_err}")
                # We do not rollback for this, but we log it. It's a best-effort side-effect.

            await session.commit()
            logger.info(f"Completed data deletion for user {user_id}: {deleted_counts}")
            
            return deleted_counts

        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to delete user data for {user_id}: {str(e)}")
            raise e

    async def export_user_data(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        Export all user data in a portable JSON format (Data Portability).
        """
        export_data = {
            "user_info": {},
            "clinical_data": {},
            "analysis_history": [],
            "documents": [],
            "consents": [],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        # User Info
        user = await session.get(User, user_id)
        if user:
            export_data["user_info"] = {
                "full_name": user.full_name,
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }

        # Clinical Data
        # Profile
        result = await session.execute(select(PatientProfile).where(PatientProfile.user_id == user_id))
        profile = result.scalars().first()
        if profile:
            export_data["clinical_data"]["profile"] = {
                "allergies": profile.allergies,
                "conditions": profile.chronic_conditions,
                "preferences": profile.preferences
            }

        # Meds
        result = await session.execute(select(PatientMedication).where(PatientMedication.user_id == user_id))
        meds = result.scalars().all()
        export_data["clinical_data"]["medications"] = [
            {"name": m.medication_name, "dosage": m.dosage, "frequency": m.frequency} for m in meds
        ]

        # Consents
        result = await session.execute(select(Consent).where(Consent.user_id == user_id))
        consents = result.scalars().all()
        export_data["consents"] = [
            {"type": c.consent_type, "accepted": c.accepted, "timestamp": c.accepted_at.isoformat() if c.accepted_at else None} for c in consents
        ]

        # Analysis History
        result = await session.execute(select(AnalysisHistory).where(AnalysisHistory.user_id == user_id))
        history = result.scalars().all()
        export_data["analysis_history"] = [
            {"timestamp": h.analysis_timestamp.isoformat(), "summary": "Full analysis data available separately"} for h in history
        ]

        return export_data
