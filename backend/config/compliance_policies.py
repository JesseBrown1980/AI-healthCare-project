"""
Compliance policies configuration for multi-regional deployments.

Defines region-specific policies for HIPAA (US), GDPR (EU), and other regions.
"""

import os
import logging
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Region codes
RegionCode = Literal["US", "EU", "APAC", "DEFAULT"]

# Supported regions
SUPPORTED_REGIONS = ["US", "EU", "APAC"]


@dataclass
class CompliancePolicy:
    """
    Compliance policy configuration for a region.
    
    Attributes:
        region: Region code (US, EU, APAC)
        retain_logs: Whether to retain application logs
        phi_in_logs: Whether PHI can appear in application logs
        require_audit_log: Whether audit logs are required
        encrypt_audit_logs: Whether audit logs should be encrypted at rest
        data_retention_days: Number of days to retain patient data (None = no automatic deletion)
        require_encryption: Whether data encryption is required
        allow_external_llm: Whether external LLM APIs can be used
        require_local_llm: Whether local LLM models must be used
        require_consent: Whether explicit user consent is required
        allow_data_deletion: Whether users can request data deletion
        require_anonymization: Whether data must be anonymized for external services
        enforce_https: Whether HTTPS is required
        require_2fa: Whether 2FA is required for patient accounts
        field_level_encryption: Whether field-level encryption is required
    """
    
    region: str
    retain_logs: bool = True
    phi_in_logs: bool = False
    require_audit_log: bool = True
    encrypt_audit_logs: bool = True
    data_retention_days: Optional[int] = None
    require_encryption: bool = True
    allow_external_llm: bool = True
    require_local_llm: bool = False
    require_consent: bool = False
    allow_data_deletion: bool = True
    require_anonymization: bool = False
    enforce_https: bool = True
    require_2fa: bool = False
    field_level_encryption: bool = False


# Region-specific policy definitions
REGION_POLICIES: Dict[str, CompliancePolicy] = {
    "US": CompliancePolicy(
        region="US",
        retain_logs=True,
        phi_in_logs=False,  # HIPAA: PHI should not be in application logs
        require_audit_log=True,  # HIPAA: Audit logs required
        encrypt_audit_logs=True,  # HIPAA: Encrypt audit logs
        data_retention_days=None,  # HIPAA: No automatic deletion requirement
        require_encryption=True,  # HIPAA: Encryption required
        allow_external_llm=True,  # HIPAA: External LLM allowed with BAA
        require_local_llm=False,
        require_consent=False,  # Covered by hospital compliance
        allow_data_deletion=True,  # HIPAA: Patients can request records
        require_anonymization=False,  # Not required if BAA in place
        enforce_https=True,
        require_2fa=False,  # Optional but recommended
        field_level_encryption=False,  # Optional
    ),
    "EU": CompliancePolicy(
        region="EU",
        retain_logs=False,  # GDPR: Minimize data retention
        phi_in_logs=False,  # GDPR: No PHI in logs
        require_audit_log=True,  # GDPR: Audit trail required
        encrypt_audit_logs=True,  # GDPR: Encrypt sensitive data
        data_retention_days=90,  # GDPR: Short retention period
        require_encryption=True,  # GDPR: Encryption required
        allow_external_llm=False,  # GDPR: Avoid cross-border data transfer
        require_local_llm=True,  # GDPR: Use EU-based or local models
        require_consent=True,  # GDPR: Explicit consent required
        allow_data_deletion=True,  # GDPR: Right to be forgotten
        require_anonymization=True,  # GDPR: Anonymize for external services
        enforce_https=True,
        require_2fa=True,  # GDPR: Strong authentication recommended
        field_level_encryption=True,  # GDPR: Enhanced security
    ),
    "APAC": CompliancePolicy(
        region="APAC",
        retain_logs=True,
        phi_in_logs=False,  # General best practice
        require_audit_log=True,
        encrypt_audit_logs=True,
        data_retention_days=None,  # Varies by country
        require_encryption=True,
        allow_external_llm=True,  # Depends on local regulations
        require_local_llm=False,
        require_consent=True,  # Many APAC countries require consent
        allow_data_deletion=True,
        require_anonymization=False,
        enforce_https=True,
        require_2fa=False,
        field_level_encryption=False,
    ),
    "DEFAULT": CompliancePolicy(
        region="DEFAULT",
        retain_logs=True,
        phi_in_logs=False,  # Safe default
        require_audit_log=True,
        encrypt_audit_logs=True,
        data_retention_days=None,
        require_encryption=True,
        allow_external_llm=True,
        require_local_llm=False,
        require_consent=False,
        allow_data_deletion=True,
        enforce_https=True,
        require_2fa=False,
        field_level_encryption=False,
    ),
}


def get_region() -> str:
    """
    Get the current deployment region from environment variable.
    
    Returns:
        Region code (US, EU, APAC, or DEFAULT)
    """
    region = os.getenv("REGION", "DEFAULT").upper()
    
    if region not in SUPPORTED_REGIONS and region != "DEFAULT":
        logger.warning(
            f"Unsupported region '{region}' specified. Using DEFAULT policy."
        )
        return "DEFAULT"
    
    return region


def get_compliance_policy(region: Optional[str] = None) -> CompliancePolicy:
    """
    Get compliance policy for a specific region.
    
    Args:
        region: Region code (US, EU, APAC). If None, uses REGION env var.
        
    Returns:
        CompliancePolicy for the specified region
    """
    if region is None:
        region = get_region()
    else:
        region = region.upper()
    
    policy = REGION_POLICIES.get(region, REGION_POLICIES["DEFAULT"])
    
    logger.debug(f"Using compliance policy for region: {policy.region}")
    
    return policy


def is_phi_allowed_in_logs() -> bool:
    """
    Check if PHI is allowed in application logs based on current region.
    
    Returns:
        True if PHI can appear in logs, False otherwise
    """
    policy = get_compliance_policy()
    return policy.phi_in_logs


def is_external_llm_allowed() -> bool:
    """
    Check if external LLM APIs are allowed based on current region.
    
    Returns:
        True if external LLM APIs can be used, False otherwise
    """
    policy = get_compliance_policy()
    return policy.allow_external_llm


def is_local_llm_required() -> bool:
    """
    Check if local LLM models are required based on current region.
    
    Returns:
        True if local LLM models must be used, False otherwise
    """
    policy = get_compliance_policy()
    return policy.require_local_llm


def is_consent_required() -> bool:
    """
    Check if explicit user consent is required based on current region.
    
    Returns:
        True if consent is required, False otherwise
    """
    policy = get_compliance_policy()
    return policy.require_consent


def get_data_retention_days() -> Optional[int]:
    """
    Get data retention period in days for current region.
    
    Returns:
        Number of days to retain data, or None if no automatic deletion
    """
    policy = get_compliance_policy()
    return policy.data_retention_days


def is_anonymization_required() -> bool:
    """
    Check if data anonymization is required for external services.
    
    Returns:
        True if anonymization is required, False otherwise
    """
    policy = get_compliance_policy()
    return policy.require_anonymization
