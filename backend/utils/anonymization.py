"""
Anonymization and pseudonymization utilities for patient data.

Provides functions to anonymize or pseudonymize patient data when sending
to external services or for analytics, ensuring compliance with regional
data protection requirements.
"""

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from uuid import uuid4

from backend.config.compliance_policies import is_anonymization_required, get_region

logger = logging.getLogger(__name__)

# Mapping of real identifiers to pseudonyms (in-memory cache)
_pseudonym_cache: Dict[str, str] = {}


def generate_pseudonym(identifier: str, salt: Optional[str] = None) -> str:
    """
    Generate a consistent pseudonym for an identifier.
    
    Args:
        identifier: Original identifier (e.g., patient ID, name)
        salt: Optional salt for hashing (for additional security)
        
    Returns:
        Pseudonym string (e.g., "PAT-abc123")
    """
    if not identifier:
        return ""
    
    # Check cache first
    cache_key = f"{salt or ''}:{identifier}"
    if cache_key in _pseudonym_cache:
        return _pseudonym_cache[cache_key]
    
    # Generate pseudonym using hash
    value_to_hash = f"{salt or ''}{identifier}".encode('utf-8')
    hash_obj = hashlib.sha256(value_to_hash)
    hash_hex = hash_obj.hexdigest()[:12]  # Use first 12 chars
    
    # Format as readable pseudonym
    pseudonym = f"PAT-{hash_hex}"
    
    # Cache it
    _pseudonym_cache[cache_key] = pseudonym
    
    return pseudonym


def anonymize_patient_name(name: str) -> str:
    """
    Anonymize a patient name.
    
    Args:
        name: Patient name
        
    Returns:
        Anonymized name (e.g., "Patient A" or pseudonym)
    """
    if not name:
        return "Anonymous Patient"
    
    # Generate pseudonym based on name
    pseudonym = generate_pseudonym(name)
    return f"Patient {pseudonym[-6:]}"  # Use last 6 chars for readability


def anonymize_date(date_str: str, preserve_year: bool = False) -> Optional[str]:
    """
    Anonymize a date by removing or generalizing it.
    
    Args:
        date_str: Date string (ISO format or other)
        preserve_year: If True, keep year but remove month/day
        
    Returns:
        Anonymized date string or None
    """
    if not date_str:
        return None
    
    try:
        # Try to parse ISO format
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(date_str)
        
        if preserve_year:
            # Keep year only
            return f"{dt.year}-XX-XX"
        else:
            # Generalize to year range (e.g., "1980s")
            decade = (dt.year // 10) * 10
            return f"{decade}s"
    except (ValueError, AttributeError):
        # If parsing fails, return generic placeholder
        return "XXXX-XX-XX"


def anonymize_age(age: int, age_ranges: bool = True) -> str:
    """
    Anonymize age by converting to age range.
    
    Args:
        age: Age in years
        age_ranges: If True, use ranges (e.g., "30-39"), else use decade
        
    Returns:
        Anonymized age representation
    """
    if age_ranges:
        # Use 10-year ranges
        range_start = (age // 10) * 10
        range_end = range_start + 9
        return f"{range_start}-{range_end}"
    else:
        # Use decade
        decade = (age // 10) * 10
        return f"{decade}s"


def pseudonymize_patient_data(
    patient_data: Dict[str, Any],
    preserve_clinical_data: bool = True,
    salt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pseudonymize patient data, replacing identifiers while preserving clinical information.
    
    Args:
        patient_data: Patient data dictionary
        preserve_clinical_data: If True, keep conditions, medications, observations
        salt: Optional salt for pseudonym generation
        
    Returns:
        Pseudonymized patient data
    """
    if not patient_data:
        return {}
    
    pseudonymized = {}
    
    # Pseudonymize patient info
    if "patient" in patient_data:
        patient = patient_data["patient"].copy()
        
        # Replace identifiers
        if "id" in patient:
            patient["id"] = generate_pseudonym(patient["id"], salt)
        if "name" in patient:
            patient["name"] = anonymize_patient_name(patient["name"])
        if "birthDate" in patient:
            patient["birthDate"] = anonymize_date(patient["birthDate"], preserve_year=False)
        
        pseudonymized["patient"] = patient
    
    # Preserve clinical data if requested
    if preserve_clinical_data:
        # Keep conditions, medications, observations (but remove patient references)
        for key in ["conditions", "medications", "observations", "encounters"]:
            if key in patient_data:
                pseudonymized[key] = patient_data[key]
    
    # Pseudonymize any patient_id references
    if "patient_id" in patient_data:
        pseudonymized["patient_id"] = generate_pseudonym(patient_data["patient_id"], salt)
    
    return pseudonymized


def anonymize_patient_data(
    patient_data: Dict[str, Any],
    preserve_clinical_data: bool = True
) -> Dict[str, Any]:
    """
    Fully anonymize patient data, removing all identifiers.
    
    Args:
        patient_data: Patient data dictionary
        preserve_clinical_data: If True, keep conditions, medications, observations
        
    Returns:
        Anonymized patient data
    """
    if not patient_data:
        return {}
    
    anonymized = {}
    
    # Remove patient identifiers
    if "patient" in patient_data:
        patient = patient_data["patient"].copy()
        
        # Remove or anonymize identifiers
        if "id" in patient:
            del patient["id"]
        if "name" in patient:
            patient["name"] = "Anonymous Patient"
        if "birthDate" in patient:
            patient["birthDate"] = anonymize_date(patient["birthDate"], preserve_year=False)
        if "age" in patient and isinstance(patient["age"], int):
            patient["age"] = anonymize_age(patient["age"])
        
        anonymized["patient"] = patient
    
    # Preserve clinical data if requested (but remove patient references)
    if preserve_clinical_data:
        for key in ["conditions", "medications", "observations", "encounters"]:
            if key in patient_data:
                # Remove any patient_id references from nested data
                anonymized[key] = [
                    {k: v for k, v in item.items() if k != "patient_id"}
                    if isinstance(item, dict)
                    else item
                    for item in patient_data[key]
                ]
    
    # Remove patient_id
    if "patient_id" in patient_data:
        del anonymized["patient_id"]
    
    return anonymized


def prepare_data_for_external_service(
    data: Dict[str, Any],
    service_type: str = "llm"
) -> Dict[str, Any]:
    """
    Prepare patient data for external service based on region compliance policy.
    
    Args:
        data: Patient data to prepare
        service_type: Type of external service ("llm", "analytics", etc.)
        
    Returns:
        Prepared data (anonymized/pseudonymized if required)
    """
    region = get_region()
    anonymization_required = is_anonymization_required()
    
    if anonymization_required:
        # Full anonymization required (e.g., EU/GDPR for external services)
        logger.info(f"Anonymizing data for external service (region: {region}, service: {service_type})")
        return anonymize_patient_data(data, preserve_clinical_data=True)
    else:
        # Pseudonymization may be sufficient (e.g., US with BAA)
        logger.debug(f"Pseudonymizing data for external service (region: {region}, service: {service_type})")
        return pseudonymize_patient_data(data, preserve_clinical_data=True)


def clear_pseudonym_cache():
    """Clear the pseudonym cache (useful for testing or security)."""
    global _pseudonym_cache
    _pseudonym_cache.clear()
    logger.debug("Pseudonym cache cleared")
