"""
Unit tests for consent management flow.

Tests consent recording, withdrawal, status checking, and region-aware requirements.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
from uuid import uuid4

from backend.services.consent_service import ConsentService
from backend.database.models import Consent
from backend.config.compliance_policies import is_consent_required


@pytest.fixture
async def db_session():
    """Create a database session for testing."""
    from backend.database import init_database, close_database, get_db_session
    
    await init_database()
    try:
        async with get_db_session() as session:
            yield session
    finally:
        await close_database()


@pytest.fixture
def consent_service():
    """Create a consent service instance."""
    return ConsentService()


@pytest.mark.asyncio
class TestConsentRecording:
    """Test consent recording functionality."""
    
    async def test_record_consent_new(self, db_session, consent_service):
        """Test recording a new consent."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        consent_type = "privacy_policy"
        version = "1.0"
        
        consent_id = await consent_service.record_consent(
            user_id=user_id,
            consent_type=consent_type,
            version=version,
            ip_address="192.168.1.1",
            user_agent="Test Agent",
            metadata={"source": "web"}
        )
        
        assert consent_id is not None
        
        # Verify consent was recorded
        status = await consent_service.get_consent_status(user_id, consent_type)
        assert status is not None
        assert status["accepted"] is True
        assert status["version"] == version
    
    async def test_record_consent_update_existing(self, db_session, consent_service):
        """Test updating an existing consent."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        consent_type = "privacy_policy"
        
        # Record initial consent
        consent_id1 = await consent_service.record_consent(
            user_id=user_id,
            consent_type=consent_type,
            version="1.0"
        )
        
        # Update consent with new version
        consent_id2 = await consent_service.record_consent(
            user_id=user_id,
            consent_type=consent_type,
            version="2.0"
        )
        
        # Should return same ID (updated existing)
        assert consent_id1 == consent_id2
        
        # Verify version was updated
        status = await consent_service.get_consent_status(user_id, consent_type)
        assert status["version"] == "2.0"
    
    async def test_record_consent_multiple_types(self, db_session, consent_service):
        """Test recording multiple consent types."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        
        # Record privacy policy consent
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="privacy_policy",
            version="1.0"
        )
        
        # Record terms of service consent
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="terms_of_service",
            version="1.0"
        )
        
        # Verify both consents exist
        all_consents = await consent_service.get_all_user_consents(user_id)
        assert "privacy_policy" in all_consents
        assert "terms_of_service" in all_consents
        assert all_consents["privacy_policy"]["accepted"] is True
        assert all_consents["terms_of_service"]["accepted"] is True


@pytest.mark.asyncio
class TestConsentWithdrawal:
    """Test consent withdrawal functionality."""
    
    async def test_withdraw_consent(self, db_session, consent_service):
        """Test withdrawing consent."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        consent_type = "privacy_policy"
        
        # Record consent first
        await consent_service.record_consent(
            user_id=user_id,
            consent_type=consent_type,
            version="1.0"
        )
        
        # Verify consent is accepted
        status = await consent_service.get_consent_status(user_id, consent_type)
        assert status["accepted"] is True
        
        # Withdraw consent
        withdrawn = await consent_service.withdraw_consent(
            user_id=user_id,
            consent_type=consent_type,
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        assert withdrawn is True
        
        # Verify consent is withdrawn
        status = await consent_service.get_consent_status(user_id, consent_type)
        assert status["accepted"] is False
        assert status["withdrawn_at"] is not None
    
    async def test_withdraw_nonexistent_consent(self, db_session, consent_service):
        """Test withdrawing consent that doesn't exist."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        
        withdrawn = await consent_service.withdraw_consent(
            user_id=user_id,
            consent_type="privacy_policy"
        )
        
        assert withdrawn is False
    
    async def test_withdraw_already_withdrawn_consent(self, db_session, consent_service):
        """Test withdrawing consent that's already withdrawn."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        consent_type = "privacy_policy"
        
        # Record and withdraw consent
        await consent_service.record_consent(user_id=user_id, consent_type=consent_type)
        await consent_service.withdraw_consent(user_id=user_id, consent_type=consent_type)
        
        # Try to withdraw again
        withdrawn = await consent_service.withdraw_consent(
            user_id=user_id,
            consent_type=consent_type
        )
        
        # Should return False (no active consent to withdraw)
        assert withdrawn is False


@pytest.mark.asyncio
class TestConsentStatus:
    """Test consent status checking."""
    
    async def test_get_consent_status_existing(self, db_session, consent_service):
        """Test getting status of existing consent."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        consent_type = "privacy_policy"
        
        await consent_service.record_consent(
            user_id=user_id,
            consent_type=consent_type,
            version="1.0"
        )
        
        status = await consent_service.get_consent_status(user_id, consent_type)
        
        assert status is not None
        assert status["user_id"] == user_id
        assert status["consent_type"] == consent_type
        assert status["accepted"] is True
        assert status["version"] == "1.0"
    
    async def test_get_consent_status_nonexistent(self, db_session, consent_service):
        """Test getting status of non-existent consent."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        
        status = await consent_service.get_consent_status(user_id, "privacy_policy")
        
        assert status is None
    
    async def test_get_all_user_consents(self, db_session, consent_service):
        """Test getting all consents for a user."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        
        # Record multiple consents
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="privacy_policy",
            version="1.0"
        )
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="terms_of_service",
            version="1.0"
        )
        
        all_consents = await consent_service.get_all_user_consents(user_id)
        
        assert isinstance(all_consents, dict)
        assert "privacy_policy" in all_consents
        assert "terms_of_service" in all_consents
        assert len(all_consents) == 2


@pytest.mark.asyncio
class TestConsentRequirements:
    """Test region-aware consent requirements."""
    
    async def test_has_required_consent_us(self, db_session, consent_service):
        """Test required consent check for US region (consent not required)."""
        with patch.dict(os.environ, {"REGION": "US"}):
            service = ConsentService()
            user_id = f"test-user-{uuid4().hex[:8]}"
            
            # US doesn't require consent
            has_consent = await service.has_required_consent(user_id)
            assert has_consent is True
    
    async def test_has_required_consent_eu_without_consent(self, db_session, consent_service):
        """Test required consent check for EU region without consent."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            service = ConsentService()
            user_id = f"test-user-{uuid4().hex[:8]}"
            
            # EU requires consent, user has none
            has_consent = await service.has_required_consent(user_id)
            assert has_consent is False
    
    async def test_has_required_consent_eu_with_partial_consent(self, db_session, consent_service):
        """Test required consent check for EU with partial consent."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            service = ConsentService()
            user_id = f"test-user-{uuid4().hex[:8]}"
            
            # Record only privacy policy (missing data_processing)
            await service.record_consent(
                user_id=user_id,
                consent_type="privacy_policy",
                version="1.0"
            )
            
            has_consent = await service.has_required_consent(user_id)
            assert has_consent is False  # Missing data_processing consent
    
    async def test_has_required_consent_eu_with_full_consent(self, db_session, consent_service):
        """Test required consent check for EU with all required consents."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            service = ConsentService()
            user_id = f"test-user-{uuid4().hex[:8]}"
            
            # Record both required consents
            await service.record_consent(
                user_id=user_id,
                consent_type="privacy_policy",
                version="1.0"
            )
            await service.record_consent(
                user_id=user_id,
                consent_type="data_processing",
                version="1.0"
            )
            
            has_consent = await service.has_required_consent(user_id)
            assert has_consent is True
    
    async def test_has_required_consent_eu_with_withdrawn_consent(self, db_session, consent_service):
        """Test required consent check when consent is withdrawn."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            service = ConsentService()
            user_id = f"test-user-{uuid4().hex[:8]}"
            
            # Record and then withdraw consent
            await service.record_consent(
                user_id=user_id,
                consent_type="privacy_policy",
                version="1.0"
            )
            await service.record_consent(
                user_id=user_id,
                consent_type="data_processing",
                version="1.0"
            )
            
            # Withdraw one consent
            await service.withdraw_consent(
                user_id=user_id,
                consent_type="privacy_policy"
            )
            
            has_consent = await service.has_required_consent(user_id)
            assert has_consent is False  # Missing required consent after withdrawal


@pytest.mark.asyncio
class TestConsentMetadata:
    """Test consent metadata handling."""
    
    async def test_record_consent_with_metadata(self, db_session, consent_service):
        """Test recording consent with metadata."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        metadata = {
            "source": "web",
            "language": "en",
            "ip_country": "US"
        }
        
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="privacy_policy",
            version="1.0",
            metadata=metadata
        )
        
        status = await consent_service.get_consent_status(user_id, "privacy_policy")
        assert status["metadata"] == metadata
    
    async def test_update_consent_metadata(self, db_session, consent_service):
        """Test updating consent metadata."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        
        # Record with initial metadata
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="privacy_policy",
            metadata={"source": "web"}
        )
        
        # Update with new metadata
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="privacy_policy",
            metadata={"source": "mobile", "app_version": "2.0"}
        )
        
        status = await consent_service.get_consent_status(user_id, "privacy_policy")
        assert status["metadata"]["source"] == "mobile"
        assert status["metadata"]["app_version"] == "2.0"


@pytest.mark.asyncio
class TestConsentIPAndUserAgent:
    """Test IP address and user agent tracking."""
    
    async def test_record_consent_with_ip_and_user_agent(self, db_session, consent_service):
        """Test recording consent with IP and user agent."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        ip_address = "192.168.1.100"
        user_agent = "Mozilla/5.0 (Test Browser)"
        
        await consent_service.record_consent(
            user_id=user_id,
            consent_type="privacy_policy",
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Note: IP and user agent are stored but not returned in get_consent_status
        # They're used for audit purposes
        status = await consent_service.get_consent_status(user_id, "privacy_policy")
        assert status is not None
        assert status["accepted"] is True
    
    async def test_withdraw_consent_with_ip_and_user_agent(self, db_session, consent_service):
        """Test withdrawing consent with IP and user agent."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        
        await consent_service.record_consent(user_id=user_id, consent_type="privacy_policy")
        
        withdrawn = await consent_service.withdraw_consent(
            user_id=user_id,
            consent_type="privacy_policy",
            ip_address="192.168.1.200",
            user_agent="Test Agent"
        )
        
        assert withdrawn is True
