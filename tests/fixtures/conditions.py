"""
Medical Condition Test Fixtures
Generates realistic condition/diagnosis data for testing.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import random
import uuid


# ICD-10 codes for common conditions
COMMON_CONDITIONS = {
    "diabetes_type2": {
        "code": "E11.9",
        "display": "Type 2 Diabetes Mellitus without complications",
        "system": "http://hl7.org/fhir/sid/icd-10",
        "severity": "medium",
    },
    "hypertension": {
        "code": "I10",
        "display": "Essential (primary) hypertension",
        "system": "http://hl7.org/fhir/sid/icd-10",
        "severity": "medium",
    },
    "heart_failure": {
        "code": "I50.9",
        "display": "Heart failure, unspecified",
        "system": "http://hl7.org/fhir/sid/icd-10",
        "severity": "high",
    },
    "ckd_stage3": {
        "code": "N18.3",
        "display": "Chronic kidney disease, stage 3",
        "system": "http://hl7.org/fhir/sid/icd-10",
        "severity": "high",
    },
    "copd": {
        "code": "J44.9",
        "display": "Chronic obstructive pulmonary disease, unspecified",
        "system": "http://hl7.org/fhir/sid/icd-10",
        "severity": "high",
    },
    "atrial_fibrillation": {
        "code": "I48.91",
        "display": "Unspecified atrial fibrillation",
        "system": "http://hl7.org/fhir/sid/icd-10",
        "severity": "high",
    },
    "obesity": {
        "code": "E66.9",
        "display": "Obesity, unspecified",
        "system": "http://hl7.org/fhir/sid/icd-10",
        "severity": "low",
    },
    "depression": {
        "code": "F32.9",
        "display": "Major depressive disorder, single episode",
        "system": "http://hl7.org/fhir/sid/icd-10",
        "severity": "medium",
    },
    "anxiety": {
        "code": "F41.9",
        "display": "Anxiety disorder, unspecified",
        "system": "http://hl7.org/fhir/sid/icd-10",
        "severity": "low",
    },
    "osteoarthritis": {
        "code": "M19.90",
        "display": "Unspecified osteoarthritis, unspecified site",
        "system": "http://hl7.org/fhir/sid/icd-10",
        "severity": "low",
    },
}


class ConditionFactory:
    """Factory for generating test condition data."""
    
    _counter = 0
    
    @classmethod
    def reset(cls):
        """Reset counter for deterministic tests."""
        cls._counter = 0
    
    @classmethod
    def create(
        cls,
        condition_key: Optional[str] = None,
        patient_id: Optional[str] = None,
        onset_date: Optional[str] = None,
        status: str = "active",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a single condition record."""
        cls._counter += 1
        
        # Pick a condition template
        if condition_key and condition_key in COMMON_CONDITIONS:
            template = COMMON_CONDITIONS[condition_key]
        else:
            key = list(COMMON_CONDITIONS.keys())[cls._counter % len(COMMON_CONDITIONS)]
            template = COMMON_CONDITIONS[key]
        
        # Generate onset date (between 1 month and 5 years ago)
        if not onset_date:
            days_ago = random.randint(30, 5 * 365)
            onset_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        return {
            "id": f"condition-{uuid.uuid4().hex[:8]}",
            "patient_id": patient_id or f"test-patient-{uuid.uuid4().hex[:8]}",
            "code": template["code"],
            "display": template["display"],
            "system": template["system"],
            "severity": template["severity"],
            "status": status,
            "onset_date": onset_date,
            "recorded_date": datetime.now().isoformat(),
            **kwargs
        }
    
    @classmethod
    def create_batch(cls, count: int, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Create multiple conditions for a patient."""
        return [cls.create(patient_id=patient_id) for _ in range(count)]


def create_sample_condition(
    condition_key: str = "diabetes_type2",
    patient_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a sample condition with specified type."""
    return ConditionFactory.create(
        condition_key=condition_key,
        patient_id=patient_id,
    )


def create_comorbidity_set(patient_id: str, severity: str = "high") -> List[Dict[str, Any]]:
    """Create a realistic set of comorbid conditions."""
    if severity == "high":
        keys = ["heart_failure", "diabetes_type2", "ckd_stage3", "atrial_fibrillation"]
    elif severity == "medium":
        keys = ["hypertension", "diabetes_type2", "obesity"]
    else:
        keys = ["anxiety", "osteoarthritis"]
    
    return [
        ConditionFactory.create(condition_key=key, patient_id=patient_id)
        for key in keys
    ]
