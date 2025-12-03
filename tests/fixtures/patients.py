"""
Patient Test Fixtures
Generates realistic but fake patient data for testing.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


# Common first and last names for generating realistic patient names
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
]


class PatientFactory:
    """Factory for generating test patient data."""
    
    _counter = 0
    
    @classmethod
    def reset(cls):
        """Reset the counter for deterministic test runs."""
        cls._counter = 0
    
    @classmethod
    def create(
        cls,
        patient_id: Optional[str] = None,
        name: Optional[str] = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        conditions: Optional[List[str]] = None,
        medications: Optional[List[str]] = None,
        risk_score: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a single patient with realistic data."""
        cls._counter += 1
        
        # Generate deterministic but realistic values
        first_name = FIRST_NAMES[cls._counter % len(FIRST_NAMES)]
        last_name = LAST_NAMES[cls._counter % len(LAST_NAMES)]
        
        return {
            "patient_id": patient_id or f"test-patient-{uuid.uuid4().hex[:8]}",
            "name": name or f"{first_name} {last_name}",
            "age": age or random.randint(25, 85),
            "gender": gender or random.choice(["male", "female"]),
            "date_of_birth": (datetime.now() - timedelta(days=365 * (age or 55))).strftime("%Y-%m-%d"),
            "conditions": conditions or [],
            "medications": medications or [],
            "risk_score": risk_score if risk_score is not None else round(random.uniform(0.1, 0.9), 2),
            "last_updated": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            **kwargs
        }
    
    @classmethod
    def create_batch(cls, count: int, **kwargs) -> List[Dict[str, Any]]:
        """Create multiple patients."""
        return [cls.create(**kwargs) for _ in range(count)]


def create_sample_patient(
    age: int = 65,
    conditions: Optional[List[str]] = None,
    medications: Optional[List[str]] = None,
    risk_score: float = 0.5,
) -> Dict[str, Any]:
    """
    Create a single sample patient with specified characteristics.
    
    Args:
        age: Patient age (default 65)
        conditions: List of condition names
        medications: List of medication names
        risk_score: Risk score 0.0-1.0
    
    Returns:
        Patient dictionary
    """
    return PatientFactory.create(
        age=age,
        conditions=conditions or ["Type 2 Diabetes", "Hypertension"],
        medications=medications or ["Metformin 500mg", "Lisinopril 10mg"],
        risk_score=risk_score,
    )


def create_high_risk_patient() -> Dict[str, Any]:
    """Create a high-risk patient for testing alert scenarios."""
    return PatientFactory.create(
        age=78,
        conditions=[
            "Chronic Heart Failure",
            "Type 2 Diabetes", 
            "Chronic Kidney Disease Stage 3",
            "Atrial Fibrillation",
            "COPD",
        ],
        medications=[
            "Metformin 1000mg BID",
            "Lisinopril 20mg daily",
            "Furosemide 40mg daily",
            "Warfarin 5mg daily",
            "Metoprolol 50mg BID",
            "Albuterol inhaler PRN",
        ],
        risk_score=0.92,
        highest_alert_severity="critical",
        active_alerts=3,
    )


def create_low_risk_patient() -> Dict[str, Any]:
    """Create a low-risk patient for baseline testing."""
    return PatientFactory.create(
        age=35,
        conditions=["Seasonal Allergies"],
        medications=["Cetirizine 10mg daily"],
        risk_score=0.15,
        highest_alert_severity="info",
        active_alerts=0,
    )


# Pre-built patient scenarios for common test cases
SAMPLE_PATIENTS = {
    "high_risk_cardiac": create_high_risk_patient,
    "low_risk_healthy": create_low_risk_patient,
    "diabetes_patient": lambda: create_sample_patient(
        conditions=["Type 2 Diabetes", "Obesity"],
        medications=["Metformin 500mg", "Ozempic 0.5mg"],
    ),
    "elderly_polypharmacy": lambda: PatientFactory.create(
        age=82,
        conditions=["Hypertension", "Osteoarthritis", "Depression", "Insomnia"],
        medications=[
            "Amlodipine 5mg", "Acetaminophen 500mg", "Sertraline 50mg",
            "Trazodone 50mg", "Omeprazole 20mg", "Calcium supplement"
        ],
        risk_score=0.68,
    ),
}
