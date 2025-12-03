"""
Unit tests for compliance policies and region configuration.

Tests region-specific compliance policies (HIPAA, GDPR, APAC).
"""

import pytest
import os
from unittest.mock import patch

from backend.config.compliance_policies import (
    get_region,
    get_compliance_policy,
    CompliancePolicy,
    RegionCode,
    is_phi_allowed_in_logs,
    is_external_llm_allowed,
    is_local_llm_required,
    is_consent_required,
    get_data_retention_days,
    is_anonymization_required,
    is_2fa_required,
    is_https_enforced,
    is_field_level_encryption_required,
)


class TestRegionConfiguration:
    """Test region configuration and retrieval."""
    
    def test_get_region_default(self):
        """Test default region when REGION env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            region = get_region()
            assert region == "DEFAULT"
    
    def test_get_region_us(self):
        """Test US region configuration."""
        with patch.dict(os.environ, {"REGION": "US"}):
            region = get_region()
            assert region == "US"
    
    def test_get_region_eu(self):
        """Test EU region configuration."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            region = get_region()
            assert region == "EU"
    
    def test_get_region_apac(self):
        """Test APAC region configuration."""
        with patch.dict(os.environ, {"REGION": "APAC"}):
            region = get_region()
            assert region == "APAC"
    
    def test_get_region_case_insensitive(self):
        """Test region is case-insensitive."""
        with patch.dict(os.environ, {"REGION": "us"}):
            region = get_region()
            assert region == "US"
    
    def test_get_region_invalid_falls_back_to_default(self):
        """Test invalid region falls back to DEFAULT."""
        with patch.dict(os.environ, {"REGION": "INVALID"}):
            region = get_region()
            assert region == "DEFAULT"


class TestCompliancePolicies:
    """Test compliance policy retrieval and properties."""
    
    def test_get_compliance_policy_us(self):
        """Test US compliance policy (HIPAA)."""
        with patch.dict(os.environ, {"REGION": "US"}):
            policy = get_compliance_policy()
            assert policy.region == "US"
            assert policy.phi_in_logs is False  # HIPAA: PHI should not be in logs
            assert policy.require_audit_log is True
            assert policy.encrypt_audit_logs is True
            assert policy.allow_external_llm is True  # Allowed with BAA
            assert policy.require_local_llm is False
            assert policy.require_consent is False
            assert policy.enforce_https is True
            assert policy.require_2fa is False  # Optional but recommended
            assert policy.field_level_encryption is False
    
    def test_get_compliance_policy_eu(self):
        """Test EU compliance policy (GDPR)."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            policy = get_compliance_policy()
            assert policy.region == "EU"
            assert policy.phi_in_logs is False  # GDPR: No PHI in logs
            assert policy.require_audit_log is True
            assert policy.encrypt_audit_logs is True
            assert policy.allow_external_llm is False  # GDPR: Avoid cross-border transfer
            assert policy.require_local_llm is True  # GDPR: Use EU-based models
            assert policy.require_consent is True  # GDPR: Explicit consent required
            assert policy.data_retention_days == 90  # GDPR: Short retention
            assert policy.allow_data_deletion is True  # GDPR: Right to be forgotten
            assert policy.require_anonymization is True
            assert policy.enforce_https is True
            assert policy.require_2fa is True  # GDPR: Strong authentication
            assert policy.field_level_encryption is True
    
    def test_get_compliance_policy_apac(self):
        """Test APAC compliance policy."""
        with patch.dict(os.environ, {"REGION": "APAC"}):
            policy = get_compliance_policy()
            assert policy.region == "APAC"
            assert policy.require_consent is True  # Many APAC countries require consent
            assert policy.enforce_https is True
    
    def test_get_compliance_policy_default(self):
        """Test DEFAULT compliance policy (safe defaults)."""
        with patch.dict(os.environ, {}, clear=True):
            policy = get_compliance_policy()
            assert policy.region == "DEFAULT"
            assert policy.phi_in_logs is False  # Safe default
            assert policy.require_encryption is True
            assert policy.enforce_https is True


class TestComplianceHelperFunctions:
    """Test compliance helper functions."""
    
    def test_is_phi_allowed_in_logs_us(self):
        """Test PHI in logs check for US region."""
        with patch.dict(os.environ, {"REGION": "US"}):
            assert is_phi_allowed_in_logs() is False
    
    def test_is_phi_allowed_in_logs_eu(self):
        """Test PHI in logs check for EU region."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert is_phi_allowed_in_logs() is False
    
    def test_is_external_llm_allowed_us(self):
        """Test external LLM allowed for US region."""
        with patch.dict(os.environ, {"REGION": "US"}):
            assert is_external_llm_allowed() is True
    
    def test_is_external_llm_allowed_eu(self):
        """Test external LLM not allowed for EU region."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert is_external_llm_allowed() is False
    
    def test_is_local_llm_required_us(self):
        """Test local LLM not required for US region."""
        with patch.dict(os.environ, {"REGION": "US"}):
            assert is_local_llm_required() is False
    
    def test_is_local_llm_required_eu(self):
        """Test local LLM required for EU region."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert is_local_llm_required() is True
    
    def test_is_consent_required_us(self):
        """Test consent not required for US region."""
        with patch.dict(os.environ, {"REGION": "US"}):
            assert is_consent_required() is False
    
    def test_is_consent_required_eu(self):
        """Test consent required for EU region."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert is_consent_required() is True
    
    def test_get_data_retention_days_us(self):
        """Test data retention days for US region (no automatic deletion)."""
        with patch.dict(os.environ, {"REGION": "US"}):
            assert get_data_retention_days() is None
    
    def test_get_data_retention_days_eu(self):
        """Test data retention days for EU region (90 days)."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert get_data_retention_days() == 90
    
    def test_is_anonymization_required_us(self):
        """Test anonymization not required for US region."""
        with patch.dict(os.environ, {"REGION": "US"}):
            assert is_anonymization_required() is False
    
    def test_is_anonymization_required_eu(self):
        """Test anonymization required for EU region."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            assert is_anonymization_required() is True


class TestSecurityCompliance:
    """Test security-related compliance settings."""
    
    def test_is_2fa_required_us(self):
        """Test 2FA not required for US region."""
        with patch.dict(os.environ, {"REGION": "US"}):
            # Note: This function may need to be added to compliance_policies.py
            policy = get_compliance_policy()
            assert policy.require_2fa is False
    
    def test_is_2fa_required_eu(self):
        """Test 2FA required for EU region."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            policy = get_compliance_policy()
            assert policy.require_2fa is True
    
    def test_https_enforcement_all_regions(self):
        """Test HTTPS enforcement is enabled for all regions."""
        for region in ["US", "EU", "APAC", "DEFAULT"]:
            with patch.dict(os.environ, {"REGION": region}):
                policy = get_compliance_policy()
                assert policy.enforce_https is True
    
    def test_field_level_encryption_us(self):
        """Test field-level encryption not required for US region."""
        with patch.dict(os.environ, {"REGION": "US"}):
            policy = get_compliance_policy()
            assert policy.field_level_encryption is False
    
    def test_field_level_encryption_eu(self):
        """Test field-level encryption required for EU region."""
        with patch.dict(os.environ, {"REGION": "EU"}):
            policy = get_compliance_policy()
            assert policy.field_level_encryption is True
