"""
FHIR Bundle Test Fixtures
Generates FHIR R4 compliant bundles for testing FHIR integrations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from .patients import PatientFactory
from .conditions import ConditionFactory, COMMON_CONDITIONS
from .medications import MedicationFactory


class FHIRBundleFactory:
    """Factory for generating FHIR R4 bundles."""
    
    @classmethod
    def create_patient_resource(cls, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert patient data to FHIR Patient resource."""
        names = patient_data.get("name", "Test Patient").split()
        return {
            "resourceType": "Patient",
            "id": patient_data.get("patient_id", str(uuid.uuid4())),
            "meta": {
                "versionId": "1",
                "lastUpdated": datetime.now().isoformat(),
            },
            "active": True,
            "name": [
                {
                    "use": "official",
                    "family": names[-1] if names else "Patient",
                    "given": names[:-1] if len(names) > 1 else ["Test"],
                }
            ],
            "gender": patient_data.get("gender", "unknown"),
            "birthDate": patient_data.get("date_of_birth", "1960-01-01"),
        }
    
    @classmethod
    def create_condition_resource(
        cls,
        condition_data: Dict[str, Any],
        patient_id: str
    ) -> Dict[str, Any]:
        """Convert condition data to FHIR Condition resource."""
        return {
            "resourceType": "Condition",
            "id": condition_data.get("id", str(uuid.uuid4())),
            "meta": {
                "lastUpdated": datetime.now().isoformat(),
            },
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active",
                    }
                ]
            },
            "code": {
                "coding": [
                    {
                        "system": condition_data.get("system", "http://hl7.org/fhir/sid/icd-10"),
                        "code": condition_data.get("code", "Z00.0"),
                        "display": condition_data.get("display", "General examination"),
                    }
                ],
                "text": condition_data.get("display", "General examination"),
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
            },
            "onsetDateTime": condition_data.get("onset_date", datetime.now().isoformat()),
        }
    
    @classmethod
    def create_medication_resource(
        cls,
        medication_data: Dict[str, Any],
        patient_id: str
    ) -> Dict[str, Any]:
        """Convert medication data to FHIR MedicationStatement resource."""
        return {
            "resourceType": "MedicationStatement",
            "id": medication_data.get("id", str(uuid.uuid4())),
            "meta": {
                "lastUpdated": datetime.now().isoformat(),
            },
            "status": medication_data.get("status", "active"),
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": medication_data.get("rxnorm_code", "unknown"),
                        "display": medication_data.get("name", "Unknown Medication"),
                    }
                ],
                "text": f"{medication_data.get('name', 'Medication')} {medication_data.get('dosage', '')}",
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
            },
            "effectiveDateTime": medication_data.get("start_date", datetime.now().isoformat()),
            "dosage": [
                {
                    "text": f"{medication_data.get('dosage', '')} {medication_data.get('frequency', '')}",
                    "route": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "26643006",
                                "display": medication_data.get("route", "oral"),
                            }
                        ]
                    },
                }
            ],
        }
    
    @classmethod
    def create_bundle(
        cls,
        resources: List[Dict[str, Any]],
        bundle_type: str = "searchset"
    ) -> Dict[str, Any]:
        """Create a FHIR Bundle containing multiple resources."""
        return {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "meta": {
                "lastUpdated": datetime.now().isoformat(),
            },
            "type": bundle_type,
            "total": len(resources),
            "entry": [
                {
                    "fullUrl": f"urn:uuid:{resource.get('id', uuid.uuid4())}",
                    "resource": resource,
                }
                for resource in resources
            ],
        }


def create_patient_bundle(
    patient_id: Optional[str] = None,
    include_conditions: bool = True,
    include_medications: bool = True,
    condition_count: int = 3,
    medication_count: int = 5,
) -> Dict[str, Any]:
    """
    Create a complete FHIR Bundle for a patient with all related resources.
    
    Args:
        patient_id: Optional patient ID (will generate if not provided)
        include_conditions: Include Condition resources
        include_medications: Include MedicationStatement resources
        condition_count: Number of conditions to include
        medication_count: Number of medications to include
    
    Returns:
        FHIR Bundle with Patient, Conditions, and Medications
    """
    # Create patient
    patient_data = PatientFactory.create(patient_id=patient_id)
    patient_id = patient_data["patient_id"]
    
    resources = [FHIRBundleFactory.create_patient_resource(patient_data)]
    
    # Add conditions
    if include_conditions:
        for _ in range(condition_count):
            condition_data = ConditionFactory.create(patient_id=patient_id)
            resources.append(
                FHIRBundleFactory.create_condition_resource(condition_data, patient_id)
            )
    
    # Add medications
    if include_medications:
        for _ in range(medication_count):
            medication_data = MedicationFactory.create(patient_id=patient_id)
            resources.append(
                FHIRBundleFactory.create_medication_resource(medication_data, patient_id)
            )
    
    return FHIRBundleFactory.create_bundle(resources)


def create_empty_bundle() -> Dict[str, Any]:
    """Create an empty FHIR Bundle (for testing no-data scenarios)."""
    return FHIRBundleFactory.create_bundle([])


def create_large_bundle(patient_count: int = 10) -> Dict[str, Any]:
    """Create a large bundle with multiple patients for pagination testing."""
    resources = []
    for _ in range(patient_count):
        patient_data = PatientFactory.create()
        resources.append(FHIRBundleFactory.create_patient_resource(patient_data))
    return FHIRBundleFactory.create_bundle(resources)
