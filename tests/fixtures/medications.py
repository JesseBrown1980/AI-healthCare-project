"""
Medication Test Fixtures
Generates realistic medication/prescription data for testing.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import random
import uuid


# RxNorm-style medication database
COMMON_MEDICATIONS = {
    "metformin": {
        "name": "Metformin",
        "rxnorm_code": "6809",
        "dosage": "500mg",
        "frequency": "twice daily",
        "route": "oral",
        "drug_class": "Biguanides",
        "indication": "Type 2 Diabetes",
    },
    "lisinopril": {
        "name": "Lisinopril",
        "rxnorm_code": "29046",
        "dosage": "10mg",
        "frequency": "once daily",
        "route": "oral",
        "drug_class": "ACE Inhibitors",
        "indication": "Hypertension",
    },
    "atorvastatin": {
        "name": "Atorvastatin",
        "rxnorm_code": "83367",
        "dosage": "20mg",
        "frequency": "once daily at bedtime",
        "route": "oral",
        "drug_class": "Statins",
        "indication": "Hyperlipidemia",
    },
    "metoprolol": {
        "name": "Metoprolol Succinate",
        "rxnorm_code": "866924",
        "dosage": "50mg",
        "frequency": "once daily",
        "route": "oral",
        "drug_class": "Beta Blockers",
        "indication": "Heart Failure/Hypertension",
    },
    "warfarin": {
        "name": "Warfarin",
        "rxnorm_code": "11289",
        "dosage": "5mg",
        "frequency": "once daily",
        "route": "oral",
        "drug_class": "Anticoagulants",
        "indication": "Atrial Fibrillation",
        "high_risk": True,
    },
    "furosemide": {
        "name": "Furosemide",
        "rxnorm_code": "4603",
        "dosage": "40mg",
        "frequency": "once daily",
        "route": "oral",
        "drug_class": "Loop Diuretics",
        "indication": "Heart Failure/Edema",
    },
    "omeprazole": {
        "name": "Omeprazole",
        "rxnorm_code": "7646",
        "dosage": "20mg",
        "frequency": "once daily before breakfast",
        "route": "oral",
        "drug_class": "Proton Pump Inhibitors",
        "indication": "GERD",
    },
    "amlodipine": {
        "name": "Amlodipine",
        "rxnorm_code": "17767",
        "dosage": "5mg",
        "frequency": "once daily",
        "route": "oral",
        "drug_class": "Calcium Channel Blockers",
        "indication": "Hypertension",
    },
    "sertraline": {
        "name": "Sertraline",
        "rxnorm_code": "36437",
        "dosage": "50mg",
        "frequency": "once daily",
        "route": "oral",
        "drug_class": "SSRIs",
        "indication": "Depression/Anxiety",
    },
    "albuterol_inhaler": {
        "name": "Albuterol Inhaler",
        "rxnorm_code": "435",
        "dosage": "90mcg/actuation",
        "frequency": "as needed",
        "route": "inhalation",
        "drug_class": "Short-Acting Beta Agonists",
        "indication": "Asthma/COPD",
    },
}


# Known drug-drug interactions for testing
DRUG_INTERACTIONS = [
    {
        "drug1": "warfarin",
        "drug2": "aspirin",
        "severity": "high",
        "description": "Increased bleeding risk",
    },
    {
        "drug1": "lisinopril",
        "drug2": "potassium_supplement",
        "severity": "medium",
        "description": "Risk of hyperkalemia",
    },
    {
        "drug1": "metformin",
        "drug2": "contrast_dye",
        "severity": "high",
        "description": "Risk of lactic acidosis",
    },
]


class MedicationFactory:
    """Factory for generating test medication data."""
    
    _counter = 0
    
    @classmethod
    def reset(cls):
        """Reset counter for deterministic tests."""
        cls._counter = 0
    
    @classmethod
    def create(
        cls,
        medication_key: Optional[str] = None,
        patient_id: Optional[str] = None,
        status: str = "active",
        start_date: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a single medication record."""
        cls._counter += 1
        
        # Pick a medication template
        if medication_key and medication_key in COMMON_MEDICATIONS:
            template = COMMON_MEDICATIONS[medication_key]
        else:
            key = list(COMMON_MEDICATIONS.keys())[cls._counter % len(COMMON_MEDICATIONS)]
            template = COMMON_MEDICATIONS[key]
        
        # Generate start date (between 1 week and 2 years ago)
        if not start_date:
            days_ago = random.randint(7, 2 * 365)
            start_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        return {
            "id": f"medication-{uuid.uuid4().hex[:8]}",
            "patient_id": patient_id or f"test-patient-{uuid.uuid4().hex[:8]}",
            "name": template["name"],
            "rxnorm_code": template["rxnorm_code"],
            "dosage": template["dosage"],
            "frequency": template["frequency"],
            "route": template["route"],
            "drug_class": template["drug_class"],
            "indication": template["indication"],
            "status": status,
            "start_date": start_date,
            "prescribed_by": "Dr. Test Provider",
            "high_risk": template.get("high_risk", False),
            **kwargs
        }
    
    @classmethod
    def create_batch(cls, count: int, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Create multiple medications for a patient."""
        return [cls.create(patient_id=patient_id) for _ in range(count)]


def create_sample_medication(
    medication_key: str = "metformin",
    patient_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a sample medication with specified type."""
    return MedicationFactory.create(
        medication_key=medication_key,
        patient_id=patient_id,
    )


def create_polypharmacy_list(patient_id: str) -> List[Dict[str, Any]]:
    """Create a polypharmacy scenario (5+ medications)."""
    keys = ["metformin", "lisinopril", "atorvastatin", "metoprolol", "omeprazole", "amlodipine"]
    return [
        MedicationFactory.create(medication_key=key, patient_id=patient_id)
        for key in keys
    ]


def create_high_risk_medication_list(patient_id: str) -> List[Dict[str, Any]]:
    """Create a list with high-risk medications."""
    keys = ["warfarin", "metformin", "furosemide"]
    return [
        MedicationFactory.create(medication_key=key, patient_id=patient_id)
        for key in keys
    ]
