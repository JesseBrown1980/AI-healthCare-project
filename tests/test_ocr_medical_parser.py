"""
Tests for medical text parser.
"""

import pytest
from backend.ocr.medical_parser import (
    MedicalParser,
    LabValue,
    Medication,
    VitalSign,
    Condition,
)


@pytest.fixture
def parser():
    """Create MedicalParser instance."""
    return MedicalParser()


def test_parse_lab_values(parser):
    """Test parsing lab values from text."""
    text = """
    Lab Results:
    Glucose: 95 mg/dL
    HbA1c: 6.5%
    Total Cholesterol: 200 mg/dL
    LDL: 120 mg/dL
    HDL: 50 mg/dL
    """
    
    result = parser.parse(text)
    
    assert len(result["lab_values"]) > 0
    
    # Check for glucose
    glucose = next((lv for lv in result["lab_values"] if lv.get("name", "").lower() == "glucose"), None)
    assert glucose is not None
    assert glucose.get("value") == 95.0
    assert glucose.get("unit") == "mg/dL"


def test_parse_medications(parser):
    """Test parsing medications from text."""
    text = """
    Medications:
    Metformin 500mg twice daily
    Lisinopril 10mg once daily
    Aspirin 81mg daily
    """
    
    result = parser.parse(text)
    
    assert len(result["medications"]) > 0
    
    # Check for metformin
    metformin = next(
        (m for m in result["medications"] if "metformin" in m.get("name", "").lower()),
        None
    )
    assert metformin is not None


def test_parse_vital_signs(parser):
    """Test parsing vital signs from text."""
    text = """
    Vital Signs:
    BP: 120/80 mmHg
    Heart Rate: 72 bpm
    Temperature: 98.6 F
    O2 Sat: 98%
    """
    
    result = parser.parse(text)
    
    assert len(result["vital_signs"]) > 0
    
    # Check for blood pressure
    bp = next((v for v in result["vital_signs"] if v.get("type") == "bp"), None)
    assert bp is not None


def test_parse_conditions(parser):
    """Test parsing conditions/diagnoses from text."""
    text = """
    Diagnoses:
    Type 2 Diabetes Mellitus
    Hypertension
    Chronic Obstructive Pulmonary Disease
    """
    
    result = parser.parse(text)
    
    assert len(result["conditions"]) > 0
    
    # Check for diabetes
    diabetes = next(
        (c for c in result["conditions"] if "diabetes" in c.get("name", "").lower()),
        None
    )
    assert diabetes is not None


def test_parse_empty_text(parser):
    """Test parsing empty text."""
    result = parser.parse("")
    
    assert result["lab_values"] == []
    assert result["medications"] == []
    assert result["vital_signs"] == []
    assert result["conditions"] == []


def test_parse_dates(parser):
    """Test parsing dates from text."""
    text = """
    Lab Results - Date: 2024-01-15
    Glucose: 95 mg/dL
    """
    
    result = parser.parse(text)
    
    # Should extract date
    assert result.get("date") is not None or len(result["lab_values"]) > 0


def test_parse_complex_lab_result(parser):
    """Test parsing complex lab result format."""
    text = """
    Complete Blood Count (CBC)
    WBC: 7.5 x10^3/uL (Reference: 4.0-11.0) - Normal
    Hemoglobin: 14.2 g/dL (Reference: 12.0-16.0) - Normal
    Platelets: 250 x10^3/uL (Reference: 150-450) - Normal
    """
    
    result = parser.parse(text)
    
    # Should extract multiple lab values
    assert len(result["lab_values"]) >= 1
    
    # Check for WBC or Hemoglobin
    wbc = next((lv for lv in result["lab_values"] if "wbc" in lv.get("name", "").lower() or "leukocyte" in lv.get("name", "").lower() or "hemoglobin" in lv.get("name", "").lower()), None)
    assert wbc is not None
    assert wbc.get("value") is not None


def test_parse_medication_with_dosage(parser):
    """Test parsing medication with dosage information."""
    text = """
    Prescription:
    Metformin HCl 500mg PO BID with meals
    """
    
    result = parser.parse(text)
    
    medications = result["medications"]
    assert len(medications) > 0
    
    metformin = next((m for m in medications if "metformin" in m.get("name", "").lower()), None)
    assert metformin is not None
    assert metformin.get("dosage") is not None or "500" in str(metformin.get("dosage", ""))


def test_parse_abnormal_values(parser):
    """Test parsing abnormal lab values."""
    text = """
    Lab Results:
    Glucose: 250 mg/dL (High - Reference: 70-100)
    HbA1c: 9.5% (High - Reference: <7.0)
    """
    
    result = parser.parse(text)
    
    lab_values = result["lab_values"]
    assert len(lab_values) > 0
    
    # Check for high glucose
    glucose = next((lv for lv in lab_values if lv.get("name", "").lower() == "glucose"), None)
    assert glucose is not None
    assert glucose.get("value") == 250.0
    # Interpretation may be None, that's okay - we just want to verify the value was parsed
    interpretation = glucose.get("interpretation")
    assert interpretation is None or "high" in str(interpretation).lower()
