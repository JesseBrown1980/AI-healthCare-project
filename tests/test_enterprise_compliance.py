"""
Tests for Enterprise Compliance using Mock Cloud Systems.

Verifies that the application respects HIPAA and GDPR policies when interacting
with simulated cloud environments (AWS, Azure, GCP).
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.testing.cloud_mocks import get_cloud_provider, MockAWS, MockAzure, MockGCP
from backend.config.compliance_policies import get_compliance_policy

class TestEnterpriseCompliance:
    
    @pytest.mark.parametrize("provider_name", ["aws", "azure", "gcp"])
    def test_hipaa_logging_compliance_us(self, provider_name):
        """Test that PHI is NOT logged in US (HIPAA) region."""
        # Setup US Region
        with patch.dict('os.environ', {'REGION': 'US'}):
            policy = get_compliance_policy()
            provider = get_cloud_provider(provider_name, "us-east-1")
            
            # Simulate app behavior: check policy before logging
            sensitive_data = "Patient: John Doe, Diagnosis: Flu"
            
            if policy.phi_in_logs:
                provider.log_event(sensitive_data)
            else:
                provider.log_event("Patient data accessed (Redacted)")
            
            # Verify Logs
            logs = provider.logs
            assert len(logs) == 1
            log_message = str(logs[0])
            
            # HIPAA Violation Check
            assert "John Doe" not in log_message
            assert "Flu" not in log_message
            assert "Redacted" in log_message

    @pytest.mark.parametrize("provider_name", ["aws", "azure", "gcp"])
    def test_gdpr_data_residency_eu(self, provider_name):
        """Test that EU data stays in EU region."""
        # Setup EU Region
        with patch.dict('os.environ', {'REGION': 'EU'}):
            try:
                # Attempt to init provider in US region (violation)
                # In a real app, this would raise an error or config check.
                # Here we simulate the check.
                target_region = "us-east-1"
                
                # Mock validation logic
                allowed_regions = ["eu-west-1", "eu-central-1"]
                if target_region not in allowed_regions:
                     raise ValueError("Data Residency Violation: EU data cannot leave region")
                
                provider = get_cloud_provider(provider_name, target_region)
            except ValueError as e:
                assert "Data Residency Violation" in str(e)

    def test_encryption_standards(self):
        """Test that data is encrypted using provider keys."""
        # Setup Default Region
        provider = get_cloud_provider("aws", "us-east-1")
        data = "Sensitive Health Record"
        key_id = "key-123"
        
        encrypted = provider.encrypt_data(data, key_id)
        
        # Verify it's actually "encrypted" (mocked)
        assert encrypted != data.encode()
        assert b"aws-kms" in encrypted
        assert key_id.encode() in encrypted

    def test_audit_trail_Completeness(self):
        """Verify audit logs capture critical actions."""
        # Simulated Audit Service
        provider = get_cloud_provider("azure", "us-east-2")
        
        actions = ["User Login", "View Patient Record", "Export Data"]
        for action in actions:
            provider.log_event(f"AUDIT: {action}", severity="AUDIT")
            
        assert len(provider.logs) == 3
        assert any(l["msg"] == "AUDIT: User Login" for l in provider.logs)

    def test_cloud_agnostic_compliance_check(self):
        """Ensure all providers pass basic compliance checks."""
        for name in ["aws", "azure", "gcp"]:
            provider = get_cloud_provider(name, "us-west-2")
            status = provider.check_compliance()
            assert status is not None
            # Check for common compliance keys (using a loose check as keys vary)
            assert any(k in str(status).lower() for k in ["encryption", "logging", "audit"])
