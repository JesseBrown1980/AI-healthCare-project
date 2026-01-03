"""
Unit tests for data deletion (GDPR right to be forgotten).

Tests data deletion functionality and region-aware policies.
"""

import pytest
import os
from unittest.mock import patch
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from backend.services.data_deletion_service import DataDeletionService
from backend.services.consent_service import ConsentService
from backend.database.models import AnalysisHistory, UserSession, Consent
from backend.config.compliance_policies import is_data_deletion_allowed
from backend.database import init_database, close_database, get_db_session


@pytest.fixture
async def db_session():
    """Create a database session for testing."""
    await init_database()
    try:
        async with get_db_session() as session:
            yield session
    finally:
        await close_database()


@pytest.fixture
def data_deletion_service():
    """Create a data deletion service instance."""
    return DataDeletionService()


class TestDataDeletionPolicy:
    """Test data deletion policy checks."""
    
    def test_is_data_deletion_allowed_us(self):
        """Test data deletion allowed for US region."""
        with patch.dict(os.environ, {"REGION": "US"}):
            assert is_data_deletion_allowed() is True
    
    def test_is_data_deletion_allowed_eu(self):
        """Test data deletion allowed for EU region (GDPR)."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert is_data_deletion_allowed() is True
    
    def test_is_data_deletion_allowed_apac(self):
        """Test data deletion allowed for APAC region."""
        with patch.dict(os.environ, {"REGION": "APAC"}):
            assert is_data_deletion_allowed() is True


@pytest.mark.asyncio
class TestDataDeletionService:
    """Test data deletion service functionality."""
    
    async def test_delete_user_data_eu(self, db_session, data_deletion_service):
        """Test deleting user data in EU region."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            service = DataDeletionService()
            user_id = f"test-user-{uuid4().hex[:8]}"
            patient_id = f"test-patient-{uuid4().hex[:8]}"
            
            # Create some test data
            async with get_db_session() as session:
                # Create analysis history
                analysis = AnalysisHistory(
                    id=str(uuid4()),
                    patient_id=patient_id,
                    user_id=user_id,
                    analysis_timestamp=datetime.now(timezone.utc),
                    analysis_data={"test": "data"},
                )
                session.add(analysis)
                
                # Create user session
                from backend.database.models import UserSession
                user_session = UserSession(
                    session_id=str(uuid4()),
                    user_id=user_id,
                    token_hash="test_hash",
                    expires_at=datetime.now(timezone.utc),
                )
                session.add(user_session)
                
                # Create consent
                consent = Consent(
                    id=str(uuid4()),
                    user_id=user_id,
                    consent_type="privacy_policy",
                    accepted=1,
                )
                session.add(consent)
                await session.commit()
            
            # Delete user data
            result = await service.delete_user_data(
                user_id=user_id,
                patient_id=patient_id,
                delete_audit_logs=False,
            )
            
            assert result["user_id"] == user_id
            assert result["region"] == "EU"
            assert result["items_deleted"]["analysis_history"] == 1
            assert result["items_deleted"]["user_sessions"] == 1
            assert result["items_deleted"]["consents_withdrawn"] == 1
    
    async def test_delete_user_data_without_permission(self, data_deletion_service):
        """Test data deletion when not allowed by policy."""
        # Create a mock policy that doesn't allow deletion
        with patch.dict(os.environ, {"REGION": "DEFAULT"}):
            # Temporarily override policy
            from backend.config.compliance_policies import REGION_POLICIES
            original_policy = REGION_POLICIES["DEFAULT"]
            REGION_POLICIES["DEFAULT"] = type(original_policy)(
                region="DEFAULT",
                allow_data_deletion=False,  # Disable deletion
            )
            
            try:
                service = DataDeletionService()
                user_id = f"test-user-{uuid4().hex[:8]}"
                
                with pytest.raises(ValueError, match="Data deletion is not allowed"):
                    await service.delete_user_data(user_id=user_id)
            finally:
                # Restore original policy
                REGION_POLICIES["DEFAULT"] = original_policy
    
    async def test_get_deletion_status(self, db_session, data_deletion_service):
        """Test getting deletion status for a user."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        
        # Create some test data
        async with get_db_session() as session:
            analysis = AnalysisHistory(
                id=str(uuid4()),
                patient_id=f"patient-{uuid4().hex[:8]}",
                user_id=user_id,
                analysis_timestamp=datetime.now(timezone.utc),
                analysis_data={},
            )
            session.add(analysis)
            await session.commit()
        
        status = await data_deletion_service.get_deletion_status(user_id)
        
        assert status["user_id"] == user_id
        assert status["data_deletion_allowed"] is True
        assert status["data_summary"]["analysis_history_count"] == 1
        assert status["data_summary"]["user_sessions_count"] == 0
        assert status["data_summary"]["consents_count"] == 0
        assert status["data_summary"]["has_2fa"] is False


@pytest.mark.asyncio
class TestDataDeletionCompliance:
    """Test data deletion respects compliance policies."""
    
    async def test_delete_with_audit_log_retention_us(self, db_session, data_deletion_service):
        """Test deletion in US region retains audit logs."""
        with patch.dict(os.environ, {"REGION": "US"}):
            service = DataDeletionService()
            user_id = f"test-user-{uuid4().hex[:8]}"
            
            result = await service.delete_user_data(
                user_id=user_id,
                delete_audit_logs=False,  # Don't delete audit logs
            )
            
            # US policy retains logs, so audit logs should not be deleted
            assert result["items_deleted"].get("audit_logs", 0) == 0
    
    async def test_delete_with_audit_log_deletion_eu(self, db_session, data_deletion_service):
        """Test deletion in EU region can delete audit logs."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            service = DataDeletionService()
            user_id = f"test-user-{uuid4().hex[:8]}"
            
            result = await service.delete_user_data(
                user_id=user_id,
                delete_audit_logs=True,  # Delete audit logs
            )
            
            # EU policy allows audit log deletion
            assert "audit_logs" in result["items_deleted"]


@pytest.mark.asyncio
class TestDataDeletionCompleteness:
    """Test that all user data is properly deleted."""
    
    async def test_delete_all_user_sessions(self, db_session, data_deletion_service):
        """Test that all user sessions are deleted."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        
        # Create multiple sessions
        async with get_db_session() as session:
            from backend.database.models import UserSession
            for i in range(3):
                session_obj = UserSession(
                    session_id=str(uuid4()),
                    user_id=user_id,
                    token_hash=f"hash_{i}",
                    expires_at=datetime.now(timezone.utc),
                )
                session.add(session_obj)
            await session.commit()
        
        result = await data_deletion_service.delete_user_data(user_id=user_id)
        
        assert result["items_deleted"]["user_sessions"] == 3
        
        # Verify deletion status shows no sessions
        status = await data_deletion_service.get_deletion_status(user_id)
        assert status["data_summary"]["user_sessions_count"] == 0
    
    async def test_withdraw_all_consents(self, db_session, data_deletion_service):
        """Test that all consents are withdrawn."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        
        # Create multiple consents
        consent_service = ConsentService()
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="privacy_policy",
        )
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="terms_of_service",
        )
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="data_processing",
        )
        
        result = await data_deletion_service.delete_user_data(user_id=user_id)
        
        assert result["items_deleted"]["consents_withdrawn"] == 3
        
        # Verify all consents are withdrawn
        all_consents = await consent_service.get_all_user_consents(user_id)
        for consent_type, consent_data in all_consents.items():
            assert consent_data["accepted"] is False
            assert consent_data["withdrawn_at"] is not None
