"""
Tests for FHIR mapper functionality.
"""

import pytest
from backend.ocr.fhir_mapper import FHIRMapper


@pytest.fixture
def mapper():
    """Create FHIRMapper instance."""
    return FHIRMapper()


def test_map_lab_values_to_observations(mapper):
    """Test mapping lab values to FHIR Observation resources."""
    parsed_data = {
        "lab_values": [
            {
                "name": "glucose",
                "value": 95.0,
                "unit": "mg/dL",
                "reference_range": "70-100",
                "interpretation": "Normal",
            },
            {
                "name": "hba1c",
                "value": 6.5,
                "unit": "%",
                "reference_range": "<7.0",
            },
        ],
        "medications": [],
        "vital_signs": [],
        "conditions": [],
    }
    
    result = mapper.map_parsed_data_to_fhir(
        parsed_data=parsed_data,
        patient_id="patient-123",
    )
    
    assert len(result["observations"]) == 2
    assert len(result["medication_statements"]) == 0
    assert len(result["conditions"]) == 0
    
    # Check first observation (glucose)
    glucose_obs = result["observations"][0]
    assert glucose_obs["resourceType"] == "Observation"
    assert glucose_obs["status"] == "final"
    assert "subject" in glucose_obs
    assert glucose_obs["subject"]["reference"] == "Patient/patient-123"
    assert "code" in glucose_obs
    assert glucose_obs["code"]["coding"][0]["code"] == "2339-0"  # LOINC for glucose


def test_map_medications_to_medication_statements(mapper):
    """Test mapping medications to FHIR MedicationStatement resources."""
    parsed_data = {
        "lab_values": [],
        "medications": [
            {
                "name": "Metformin",
                "dosage": "500mg",
                "frequency": "twice daily",
                "route": "PO",
            },
            {
                "name": "Lisinopril",
                "dosage": "10mg",
                "frequency": "once daily",
            },
        ],
        "vital_signs": [],
        "conditions": [],
    }
    
    result = mapper.map_parsed_data_to_fhir(
        parsed_data=parsed_data,
        patient_id="patient-123",
    )
    
    assert len(result["medication_statements"]) == 2
    assert len(result["observations"]) == 0
    
    # Check first medication
    metformin = result["medication_statements"][0]
    assert metformin["resourceType"] == "MedicationStatement"
    assert metformin["status"] == "active"
    assert "subject" in metformin
    assert metformin["subject"]["reference"] == "Patient/patient-123"
    assert "medicationCodeableConcept" in metformin


def test_map_vital_signs_to_observations(mapper):
    """Test mapping vital signs to FHIR Observation resources."""
    parsed_data = {
        "lab_values": [],
        "medications": [],
        "vital_signs": [
            {
                "type": "bp",
                "value": 120.0,
                "unit": "mmHg",
            },
            {
                "type": "hr",
                "value": 72.0,
                "unit": "bpm",
            },
        ],
        "conditions": [],
    }
    
    result = mapper.map_parsed_data_to_fhir(
        parsed_data=parsed_data,
        patient_id="patient-123",
    )
    
    assert len(result["observations"]) == 2
    
    # Check blood pressure observation
    bp_obs = result["observations"][0]
    assert bp_obs["resourceType"] == "Observation"
    assert bp_obs["code"]["coding"][0]["code"] == "85354-9"  # LOINC for BP panel


def test_map_conditions_to_condition_resources(mapper):
    """Test mapping conditions to FHIR Condition resources."""
    parsed_data = {
        "lab_values": [],
        "medications": [],
        "vital_signs": [],
        "conditions": [
            {
                "name": "Type 2 Diabetes Mellitus",
                "code": None,
            },
            {
                "name": "Hypertension",
                "code": None,
            },
        ],
    }
    
    result = mapper.map_parsed_data_to_fhir(
        parsed_data=parsed_data,
        patient_id="patient-123",
    )
    
    assert len(result["conditions"]) == 2
    
    # Check first condition
    diabetes = result["conditions"][0]
    assert diabetes["resourceType"] == "Condition"
    assert diabetes["subject"]["reference"] == "Patient/patient-123"
    assert "code" in diabetes


def test_map_with_document_reference(mapper):
    """Test mapping with document reference."""
    parsed_data = {
        "lab_values": [
            {
                "name": "glucose",
                "value": 95.0,
                "unit": "mg/dL",
            },
        ],
        "medications": [],
        "vital_signs": [],
        "conditions": [],
    }
    
    result = mapper.map_parsed_data_to_fhir(
        parsed_data=parsed_data,
        patient_id="patient-123",
        document_id="doc-456",
    )
    
    assert result["document_reference"] is not None
    doc_ref = result["document_reference"]
    assert doc_ref["resourceType"] == "DocumentReference"
    assert doc_ref["subject"]["reference"] == "Patient/patient-123"
    assert doc_ref["id"] == "doc-456"


def test_map_empty_parsed_data(mapper):
    """Test mapping empty parsed data."""
    parsed_data = {
        "lab_values": [],
        "medications": [],
        "vital_signs": [],
        "conditions": [],
    }
    
    result = mapper.map_parsed_data_to_fhir(
        parsed_data=parsed_data,
        patient_id="patient-123",
    )
    
    assert len(result["observations"]) == 0
    assert len(result["medication_statements"]) == 0
    assert len(result["conditions"]) == 0
    assert result["document_reference"] is None


def test_map_with_loinc_codes(mapper):
    """Test that LOINC codes are correctly assigned."""
    parsed_data = {
        "lab_values": [
            {"name": "glucose", "value": 95.0, "unit": "mg/dL"},
            {"name": "cholesterol", "value": 200.0, "unit": "mg/dL"},
            {"name": "ldl", "value": 120.0, "unit": "mg/dL"},
            {"name": "hdl", "value": 50.0, "unit": "mg/dL"},
        ],
        "medications": [],
        "vital_signs": [],
        "conditions": [],
    }
    
    result = mapper.map_parsed_data_to_fhir(
        parsed_data=parsed_data,
        patient_id="patient-123",
    )
    
    # Check that each observation has correct LOINC code
    loinc_codes = {
        "glucose": "2339-0",
        "cholesterol": "2093-3",
        "ldl": "2089-1",
        "hdl": "2085-9",
    }
    
    for obs in result["observations"]:
        code = obs["code"]["coding"][0]["code"]
        assert code in loinc_codes.values()
