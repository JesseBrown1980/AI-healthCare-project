"""
PHI (Protected Health Information) filtering utilities.

Provides functions to mask or filter PHI from logs and other outputs
based on region-specific compliance policies.
"""

import re
import hashlib
import logging
from typing import Any, Dict, Optional, Union, List
from datetime import datetime

from backend.config.compliance_policies import is_phi_allowed_in_logs

logger = logging.getLogger(__name__)

# Common PHI patterns
PHI_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN: 123-45-6789
    "phone": re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),  # Phone numbers
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "patient_id": re.compile(r"\bpatient[-_]?\d+\b", re.IGNORECASE),
    "mrn": re.compile(r"\bmrn[-:]?\s*\d+\b", re.IGNORECASE),  # Medical Record Number
    "date_of_birth": re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),  # Dates
    "zip_code": re.compile(r"\b\d{5}(-\d{4})?\b"),  # ZIP codes
}

# Common PHI field names (case-insensitive)
PHI_FIELD_NAMES = {
    "name", "patient_name", "first_name", "last_name", "full_name",
    "email", "email_address", "phone", "phone_number", "telephone",
    "address", "street_address", "city", "state", "zip", "zip_code",
    "ssn", "social_security_number", "patient_id", "mrn", "medical_record_number",
    "birth_date", "date_of_birth", "dob", "age",
    "insurance_id", "insurance_number", "policy_number",
    "diagnosis", "condition", "medication", "prescription",
}


def mask_phi_value(value: Any, mask_char: str = "*") -> str:
    """
    Mask a PHI value, preserving length and format.
    
    Args:
        value: Value to mask
        mask_char: Character to use for masking
        
    Returns:
        Masked string
    """
    if value is None:
        return "[REDACTED]"
    
    value_str = str(value)
    
    # If it's a short value, mask completely
    if len(value_str) <= 4:
        return mask_char * len(value_str)
    
    # For longer values, show first and last characters
    if len(value_str) <= 8:
        return value_str[0] + mask_char * (len(value_str) - 2) + value_str[-1]
    else:
        # Show first 2 and last 2 characters
        return value_str[:2] + mask_char * (len(value_str) - 4) + value_str[-2:]


def hash_phi_value(value: Any, salt: Optional[str] = None) -> str:
    """
    Hash a PHI value for consistent but anonymized representation.
    
    Args:
        value: Value to hash
        salt: Optional salt for hashing
        
    Returns:
        Hashed string (first 8 characters of SHA256)
    """
    if value is None:
        return "[REDACTED]"
    
    value_str = str(value)
    if salt:
        value_str = f"{salt}{value_str}"
    
    hash_obj = hashlib.sha256(value_str.encode())
    return f"HASH:{hash_obj.hexdigest()[:8]}"


def mask_text(text: str, mask_char: str = "*") -> str:
    """
    Mask PHI patterns in a text string.
    
    Args:
        text: Text to mask
        mask_char: Character to use for masking
        
    Returns:
        Text with PHI patterns masked
    """
    if not text:
        return text
    
    masked_text = text
    
    # Mask SSNs
    masked_text = PHI_PATTERNS["ssn"].sub(lambda m: mask_phi_value(m.group(), mask_char), masked_text)
    
    # Mask phone numbers
    masked_text = PHI_PATTERNS["phone"].sub(lambda m: mask_phi_value(m.group(), mask_char), masked_text)
    
    # Mask email addresses (keep domain visible for debugging)
    def mask_email(match):
        email = match.group()
        local, domain = email.split("@", 1)
        masked_local = mask_phi_value(local, mask_char)
        return f"{masked_local}@{domain}"
    
    masked_text = PHI_PATTERNS["email"].sub(mask_email, masked_text)
    
    # Mask patient IDs and MRNs
    masked_text = PHI_PATTERNS["patient_id"].sub(lambda m: mask_phi_value(m.group(), mask_char), masked_text)
    masked_text = PHI_PATTERNS["mrn"].sub(lambda m: mask_phi_value(m.group(), mask_char), masked_text)
    
    return masked_text


def filter_phi_from_dict(
    data: Dict[str, Any],
    mask_char: str = "*",
    use_hash: bool = False,
    preserve_keys: bool = True
) -> Dict[str, Any]:
    """
    Filter PHI from a dictionary, masking or hashing values.
    
    Args:
        data: Dictionary to filter
        mask_char: Character to use for masking
        use_hash: If True, hash values instead of masking
        preserve_keys: If True, keep keys but mask values; if False, remove PHI keys
        
    Returns:
        Dictionary with PHI filtered
    """
    if not data:
        return data
    
    filtered = {}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Check if this is a PHI field
        is_phi_field = any(phi_name in key_lower for phi_name in PHI_FIELD_NAMES)
        
        if is_phi_field:
            if preserve_keys:
                # Mask or hash the value
                if use_hash:
                    filtered[key] = hash_phi_value(value)
                else:
                    filtered[key] = mask_phi_value(value, mask_char)
            # If preserve_keys is False, skip this field entirely
        elif isinstance(value, dict):
            # Recursively filter nested dictionaries
            filtered[key] = filter_phi_from_dict(value, mask_char, use_hash, preserve_keys)
        elif isinstance(value, list):
            # Filter list items
            filtered[key] = [
                filter_phi_from_dict(item, mask_char, use_hash, preserve_keys)
                if isinstance(item, dict)
                else (mask_text(str(item), mask_char) if isinstance(item, str) else item)
                for item in value
            ]
        elif isinstance(value, str):
            # Mask PHI patterns in strings
            filtered[key] = mask_text(value, mask_char)
        else:
            # Keep non-PHI values as-is
            filtered[key] = value
    
    return filtered


def filter_phi_from_log_data(
    log_data: Dict[str, Any],
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Filter PHI from log data based on region compliance policy.
    
    Args:
        log_data: Log data dictionary
        region: Region code (if None, uses current region from env)
        
    Returns:
        Log data with PHI filtered if required by region policy
    """
    # Check if PHI is allowed in logs for this region
    if is_phi_allowed_in_logs():
        # PHI is allowed, return as-is
        return log_data
    
    # PHI is not allowed, filter it
    return filter_phi_from_dict(log_data, preserve_keys=True, use_hash=False)


def sanitize_for_logging(
    value: Any,
    field_name: Optional[str] = None
) -> Any:
    """
    Sanitize a value for logging based on field name and region policy.
    
    Args:
        value: Value to sanitize
        field_name: Optional field name to check against PHI field names
        
    Returns:
        Sanitized value
    """
    # Check if PHI is allowed
    if is_phi_allowed_in_logs():
        return value
    
    # Check if field name indicates PHI
    if field_name:
        field_lower = field_name.lower()
        if any(phi_name in field_lower for phi_name in PHI_FIELD_NAMES):
            return mask_phi_value(value)
    
    # If value is a string, check for PHI patterns
    if isinstance(value, str):
        return mask_text(value)
    
    # If value is a dict, filter it
    if isinstance(value, dict):
        return filter_phi_from_dict(value)
    
    # Otherwise return as-is
    return value
