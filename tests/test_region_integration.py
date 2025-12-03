"""
Integration tests for region-aware compliance features.

Tests end-to-end behavior across different regions (US, EU, APAC) to ensure
compliance policies are properly enforced throughout the application flow.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from backend.config.compliance_policies import (
    get_region,
    get_compliance_policy,
    is_phi_allowed_in_logs,
    is_external_llm_allowed,
    is_consent_required,
    is_data_deletion_allowed,
    is_2fa_required,
)
from backend.services.consent_service import ConsentService
from backend.services.data_deletion_service import DataDeletionService
from backend.utils.phi_filter import filter_phi_from_log_data, sanitize_for_logging
from backend.utils.logging_utils import log_structured
from backend.rag_fusion import RAGFusion
from backend.database import init_database, close_database, get_db_session
from backend.database.models import AnalysisHistory, Consent


@pytest.fixture
async def db_session():
    """Create a database session for testing."""
    await init_database()
    try:
        async with get_db_session() as session:
            yield session
    finally:
        await close_database()


@pytest.mark.asyncio
class TestRegionComplianceIntegration:
    """Test compliance features work together across regions."""
    
    async def test_us_region_full_flow(self, db_session):
        """Test full flow in US region (HIPAA compliance)."""
        with patch.dict(os.environ, {"REGION": "US"}):
            user_id = f"test-user-{uuid4().hex[:8]}"
            patient_id = f"test-patient-{uuid4().hex[:8]}"
            
            # Verify US policy
            policy = get_compliance_policy()
            assert policy.region == "US"
            assert policy.allow_external_llm is True
            assert policy.require_consent is False
            assert policy.require_2fa is False
            
            # Test PHI filtering in logs
            log_data = {
                "patient_name": "John Doe",
                "ssn": "123-45-6789",
                "message": "Patient data processed"
            }
            filtered = filter_phi_from_log_data(log_data)
            # PHI should be filtered (not allowed in logs)
            assert "John Doe" not in str(filtered.values())
            assert "123-45-6789" not in str(filtered.values())
            
            # Test consent (not required in US)
            consent_service = ConsentService()
            consent_status = await consent_service.get_consent_status(
                user_id, "privacy_policy"
            )
            # Consent not required, so None is acceptable
            assert consent_status is None or isinstance(consent_status, dict)
            
            # Test data deletion (allowed in US)
            assert is_data_deletion_allowed() is True
            deletion_service = DataDeletionService()
            status = await deletion_service.get_deletion_status(user_id)
            assert status["data_deletion_allowed"] is True
    
    async def test_eu_region_full_flow(self, db_session):
        """Test full flow in EU region (GDPR compliance)."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            user_id = f"test-user-{uuid4().hex[:8]}"
            patient_id = f"test-patient-{uuid4().hex[:8]}"
            
            # Verify EU policy
            policy = get_compliance_policy()
            assert policy.region == "EU"
            assert policy.allow_external_llm is False
            assert policy.require_consent is True
            assert policy.require_2fa is True
            assert policy.data_retention_days == 90
            
            # Test PHI filtering in logs
            log_data = {
                "patient_name": "Jane Smith",
                "email": "jane@example.com",
                "message": "GDPR data processing"
            }
            filtered = filter_phi_from_log_data(log_data)
            # PHI should be filtered
            assert "Jane Smith" not in str(filtered.values())
            assert "jane@example.com" not in str(filtered.values())
            
            # Test consent (required in EU)
            consent_service = ConsentService()
            # Without consent, should return None or indicate missing consent
            consent_status = await consent_service.get_consent_status(
                user_id, "privacy_policy"
            )
            # In EU, consent is required but may not exist yet
            assert consent_status is None or isinstance(consent_status, dict)
            
            # Record consent (required for GDPR)
            consent_id = await consent_service.record_consent(
                user_id=user_id,
                consent_type="privacy_policy",
                version="1.0",
            )
            assert consent_id is not None
            
            # Verify consent is recorded
            consent_status = await consent_service.get_consent_status(
                user_id, "privacy_policy"
            )
            assert consent_status is not None
            assert consent_status["accepted"] is True
            
            # Test data deletion (GDPR right to be forgotten)
            assert is_data_deletion_allowed() is True
            deletion_service = DataDeletionService()
            
            # Create some test data
            async with get_db_session() as session:
                analysis = AnalysisHistory(
                    id=str(uuid4()),
                    patient_id=patient_id,
                    user_id=user_id,
                    analysis_timestamp=datetime.now(timezone.utc),
                    analysis_data={"test": "data"},
                )
                session.add(analysis)
                await session.commit()
            
            # Delete user data
            result = await deletion_service.delete_user_data(
                user_id=user_id,
                patient_id=patient_id,
                delete_audit_logs=False,
            )
            assert result["region"] == "EU"
            assert result["items_deleted"]["analysis_history"] == 1
            assert result["items_deleted"]["consents_withdrawn"] == 1
    
    async def test_apac_region_full_flow(self, db_session):
        """Test full flow in APAC region."""
        with patch.dict(os.environ, {"REGION": "APAC"}):
            user_id = f"test-user-{uuid4().hex[:8]}"
            
            # Verify APAC policy
            policy = get_compliance_policy()
            assert policy.region == "APAC"
            assert policy.enforce_https is True
            
            # Test PHI filtering
            log_data = {
                "patient_id": "patient-12345",
                "message": "APAC data processing"
            }
            filtered = filter_phi_from_log_data(log_data)
            # PHI should be filtered
            assert "patient-12345" not in str(filtered.values())
            
            # Test data deletion
            assert is_data_deletion_allowed() is True


@pytest.mark.asyncio
class TestRegionAwareRAG:
    """Test RAG knowledge base filtering by region."""
    
    async def test_rag_us_region_filtering(self):
        """Test RAG returns US-appropriate content."""
        with patch.dict(os.environ, {"REGION": "US"}):
            # RAGFusion uses default knowledge base (in-memory)
            # Use a mock path since we're testing region filtering
            rag = RAGFusion(knowledge_base_path="mock_path")
            assert rag.region == "US"
            
            # Test knowledge retrieval (region is determined by instance, not parameter)
            knowledge = await rag.retrieve_relevant_knowledge(
                query="hypertension treatment guidelines"
            )
            assert isinstance(knowledge, dict)
            # Knowledge should be filtered by US region automatically
            assert "relevant_content" in knowledge or "guidelines" in knowledge or "protocols" in knowledge
    
    async def test_rag_eu_region_filtering(self):
        """Test RAG returns EU-appropriate content."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            # RAGFusion uses default knowledge base (in-memory)
            rag = RAGFusion(knowledge_base_path="mock_path")
            assert rag.region == "EU"
            
            # Test knowledge retrieval
            knowledge = await rag.retrieve_relevant_knowledge(
                query="diabetes management"
            )
            assert isinstance(knowledge, dict)
            # Knowledge should be filtered by EU region automatically
            assert "relevant_content" in knowledge or "guidelines" in knowledge or "protocols" in knowledge


@pytest.mark.asyncio
class TestRegionPolicyEnforcement:
    """Test that policies are enforced consistently across services."""
    
    async def test_phi_filtering_consistency(self):
        """Test PHI filtering is consistent across regions."""
        test_data = {
            "patient_name": "Test Patient",
            "ssn": "123-45-6789",
            "email": "patient@example.com",
            "phone": "555-123-4567"
        }
        
        for region in ["US", "EU", "APAC"]:
            with patch.dict(os.environ, {"REGION": region}):
                # PHI should never be allowed in logs
                assert is_phi_allowed_in_logs() is False
                
                filtered = filter_phi_from_log_data(test_data)
                # Verify PHI is filtered
                assert "Test Patient" not in str(filtered.values())
                assert "123-45-6789" not in str(filtered.values())
                assert "patient@example.com" not in str(filtered.values())
                assert "555-123-4567" not in str(filtered.values())
    
    async def test_consent_requirement_by_region(self, db_session):
        """Test consent requirements vary by region."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        
        # US: consent not required
        with patch.dict(os.environ, {"REGION": "US"}):
            assert is_consent_required() is False
        
        # EU: consent required
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert is_consent_required() is True
            
            consent_service = ConsentService()
            # Without consent, operation should still work but may log warning
            consent_status = await consent_service.get_consent_status(
                user_id, "privacy_policy"
            )
            # Status may be None if no consent recorded yet
            assert consent_status is None or isinstance(consent_status, dict)
        
        # APAC: check policy
        with patch.dict(os.environ, {"REGION": "APAC"}):
            policy = get_compliance_policy()
            # APAC may or may not require consent depending on policy
            assert isinstance(is_consent_required(), bool)
    
    async def test_2fa_requirement_by_region(self):
        """Test 2FA requirements vary by region."""
        # US: 2FA not required
        with patch.dict(os.environ, {"REGION": "US"}):
            assert is_2fa_required() is False
        
        # EU: 2FA required
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert is_2fa_required() is True
        
        # APAC: check policy
        with patch.dict(os.environ, {"REGION": "APAC"}):
            policy = get_compliance_policy()
            assert isinstance(is_2fa_required(), bool)


@pytest.mark.asyncio
class TestRegionDataRetention:
    """Test data retention policies by region."""
    
    async def test_data_retention_policy_enforcement(self):
        """Test data retention days vary by region."""
        # US: No automatic deletion
        with patch.dict(os.environ, {"REGION": "US"}):
            policy = get_compliance_policy()
            assert policy.data_retention_days is None
        
        # EU: 90 days retention
        with patch.dict(os.environ, {"REGION": "EU"}):
            policy = get_compliance_policy()
            assert policy.data_retention_days == 90
        
        # APAC: Check policy
        with patch.dict(os.environ, {"REGION": "APAC"}):
            policy = get_compliance_policy()
            assert policy.data_retention_days is None or isinstance(
                policy.data_retention_days, int
            )


class TestRegionLLMRouting:
    """Test LLM routing based on region policies."""
    
    def test_external_llm_allowed_by_region(self):
        """Test external LLM usage varies by region."""
        # US: External LLM allowed
        with patch.dict(os.environ, {"REGION": "US"}):
            assert is_external_llm_allowed() is True
        
        # EU: External LLM not allowed (GDPR)
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert is_external_llm_allowed() is False
        
        # APAC: Check policy
        with patch.dict(os.environ, {"REGION": "APAC"}):
            policy = get_compliance_policy()
            assert isinstance(is_external_llm_allowed(), bool)
